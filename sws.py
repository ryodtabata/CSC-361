import socket 
import select
import sys
import queue
import re
import time
import datetime


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#makes the socket 
server.setblocking(0)
#allows dealing with multiple sockets at once 
serverPort = int(sys.argv[2])
#server number given as argument
server_address = ('', serverPort)
#server address tuple 
server.bind(server_address)
#Listen for incoming connections
server.listen(5)
inputs = [server]
outputs = []

timeout = 100

response_messages = {}

request_messages = {}

consistent_socket = {}

final_message = {}

logtup = {}
    
def print_log(s):
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%a %b %d %X PST %Y").strip()
    logstamp = ((time_string+': '+str(s.getpeername()[0])+':'+str(s.getpeername()[1])+' '+logtup[s][0]+';'+logtup[s][1]))
    print(logstamp)
    logtup[s] = ['','',datetime.datetime.now()]

while inputs:
    readable, writeable, exceptional = select.select(inputs, outputs, inputs, timeout)
    
    for s in readable:
        
        if s is server:
            connectionSocket, addr = server.accept()
            connectionSocket.setblocking(0)
            inputs.append(connectionSocket)
            request_messages[connectionSocket] = ''
            consistent_socket[connectionSocket] = False
            response_messages[connectionSocket] = queue.Queue()
            final_message[connectionSocket] = ''
            logtup[connectionSocket] = ['','',datetime.datetime.now()]
        
        else: 
            s.setblocking(1)
            message1 = s.recv(1024).decode()
            if (message1 and message1!=('\n')):
                logtup[2] = datetime.datetime.now()
                logtup[s][0] = message1
                if s not in outputs: 
                    outputs.append(s)
                valid = re.compile('^GET /[A-Za-z0-9_.-]+ HTTP/1.0$')
                if valid.search(message1):
                    #good message add it to request 
                    request_messages[s] = request_messages[s] + message1 
                    message = request_messages[s]
                    while message [-2:] != '\n\n':
                        message2 = s.recv(1024).decode()
                        request_messages[s] = request_messages[s] + message2 
                        message = request_messages[s]
                        #because if its space only i will get an error
                    if (len(message)>2):   
                        #looking for the filename using indexing
                        start_index = request_messages[s].find("/")
                        end_index = request_messages[s].find(" ", start_index)
                        nameoffile = request_messages[s][start_index+1: end_index]
                    
                        #finding if the connection is persistent or not
                        #change so its completely case insenseitive 
                        lowercase = request_messages[s].lower()
                        connection_type = (lowercase.find("\nconnection: keep-alive")!=-1) or (lowercase.find("\nconnection:keep-alive")!=-1)

                        
                        if connection_type:
                            consistent_socket[s] = True
                        
                        try:
                            f=open(nameoffile, 'r')
                            outputtext = f.read()
                            f.close()
                            if consistent_socket[s] == True:
                                response_messages[s].put_nowait('HTTP/1.0 200 OK\r\nConnection: keep-alive\r\n\r\n')
                                logtup[s][1] = 'HTTP/1.0 200 OK'
                               
                            else:
                                response_messages[s].put_nowait('HTTP/1.0 200 OK\r\nConnection: close\r\n\r\n')
                                logtup[s][1] = 'HTTP/1.0 200 OK'
                                
                            response_messages[s].put_nowait(outputtext)
                        
                        except IOError:
                            if consistent_socket[s] == True:
                                response_messages[s].put_nowait('HTTP/1.0 404 Not Found\r\nConnection: keep-alive\r\n\r\n')
                                logtup[s][1] = 'HTTP/1.0 404 Not Found'
                        
         
                            else:
                                response_messages[s].put_nowait('HTTP/1.0 404 Not Found\r\nConnection: close\r\n\r\n')
                                logtup[s][1] = 'HTTP/1.0 404 Not Found'
                    
                else:
                    response_messages[s].put_nowait('HTTP/1.0 400 Bad Request\r\nConnection: close\r\n\r\n')
                    logtup[s][1] = 'HTTP/1.0 400 Bad Request'

   
    for s in writeable:
        
        try:
            next_msg = response_messages[s].get_nowait()
            final_message[s]+= (next_msg)
            
        except queue.Empty:
            delta = datetime.datetime.now() - logtup[s][2]
            if (delta.total_seconds() > timeout):
                print("Server timeout")
                inputs.remove(s)
                outputs.remove(s)
                del response_messages[s]
                del request_messages[s]
                del final_message[s]
                del logtup[s]
                del consistent_socket[s]
                s.close()
                break
                
            
            elif consistent_socket[s] == False:
                print_log(s)
                if s in inputs:
                    inputs.remove(s)
                if s in outputs:
                    outputs.remove(s)
                del response_messages[s]
                del request_messages[s]
                del final_message[s]
                del logtup[s]
                del consistent_socket[s]
                s.close()
            
            else:
                print_log(s)
                consistent_socket[s] = False
                if s in outputs:
                    outputs.remove(s)
                request_messages[s] = ''
                final_message[s] = ''
                logtup[s] = ['','',datetime.datetime.now()]
                
        else:
            s.send(final_message[s].encode())
            final_message[s] = '' 
   
    for s in exceptional:
        if s in inputs:
            inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
        del request_messages[s]
        del consistent_socket[s]
        del response_messages[s]
        del final_message[s]
        del logtup[s]
        
          
    if s not in readable and writeable and exceptional:
        x=1
        #avoding EOF
