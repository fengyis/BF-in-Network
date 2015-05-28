import socket
import sys
import json
import select
import copy
import threading
import time
import os
import base64
import math
import traceback
MSS=512.0

def send_update():
    lock.acquire()
    for neighbor in copy.deepcopy(neighbors_table):
        neighbor_host, neighbor_port = neighbor.split(':')
        packet = {
            'source':this_node,
            'command': 'update',
            'routing_table': {}
        }
        for dest in routing_table:
            packet['routing_table'][dest] = copy.deepcopy(routing_table[dest])

            # poison reverse
           
            if dest != neighbor and routing_table[dest]['next_hop'] == neighbor:
                 packet['routing_table'][dest]['cost'] = float('inf')
        router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))
    lock.release()
def check_nodes():


    
    while True:
        lock.acquire()
        for neighbor in copy.deepcopy(neighbors_table):
            if neighbor in copy.deepcopy(timer_records): #dictionary changed size during iteration error
               
                if int(round(time.time() * 1000)) > (timer_records[neighbor] + period*3000):
                    #print "check_nodes"+str(neighbor)

                    del neighbors_table[neighbor]
                    del timer_records[neighbor]
                    if routing_table[neighbor]['cost']!=float('inf'):
                      
                        routing_table[neighbor]['cost']=float('inf')
                        routing_table[neighbor]['next_hop']=''

                        

                        for dest in routing_table:
                            if dest in neighbors_table:
                                routing_table[dest]['cost']=neighbor_links[dest]
                                routing_table[dest]['next_hop']=dest
                            else:
                                routing_table[dest]['cost']=float('inf')
                                routing_table[dest]['next_hop']=''
                        packet={
                            'command':'close',
                            'close_node':neighbor
                        }

                        for neighbor in neighbors_table:
                            neighbor_host, neighbor_port=neighbor.split(':')
                            router_socket.sendto(json.dumps(packet),(neighbor_host,int(neighbor_port)))
                    else:
                        send_update()
        lock.release()
        time.sleep(period)    

def periodic_update(interval):
    while True:
        send_update()
        time.sleep(interval)





if __name__ == '__main__':
    host = socket.gethostbyname(socket.gethostname())
    
    #host='127.0.0.1'
    print host
    routing_table = {}
    neighbors_table = {}
    
    neighbor_links = {}

    timer_records = {}
    link_down=[]
    link_change_list={}
    seq_num_list=[]
    file_buffer=[]
 
    lock=threading.RLock()
    file_name = sys.argv[1]
    with open(file_name) as config_file:
        first_line = config_file.readline()
        words = first_line.split()
        port = int(words[0])
        period = int(words[1])

   

        # string identifier for this node
        this_node = host + ':' + str(port)

        # initialize neighbors in routing table
        for line in config_file:
            words = line.split()
            neighbor = words[0]
            neighbor_cost = float(words[1])
            neighbors_table[neighbor] = {}

            routing_table[neighbor] = {}
            routing_table[neighbor]['cost'] = neighbor_cost

            routing_table[neighbor]['next_hop'] = neighbor
            neighbor_links[neighbor] = neighbor_cost
            timer_records[neighbor]=int(round(time.time()*1000))



    router_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    router_socket.bind((host, port))
    
    print '\nClient started.\nHOST: ' + host + '\n PORT: ' + str(port)
    print 'Bellman-Ford algorithm.\n'

    print "This is the current routing table"
    print json.dumps(routing_table, indent=4)
    print "The neighbors are"
    print json.dumps(neighbors_table,indent=4)

    send_update()   
    threading.Thread(target=periodic_update,args=[period]).start()
    threading.Thread(target=check_nodes,args=[]).start()

    while True:
        #Monitor the status of socket and system terminal
        read_sockets,write_sockets,error_sockets = select.select([sys.stdin,router_socket],[],[])
        for sock in read_sockets:
           
          

            if sock == router_socket:
                
                r, addr = sock.recvfrom(20480)
                data = json.loads(r)
                
                sender = addr[0] + ':' + str(addr[1])


                if data['command'] == 'update':
                    #print "update at "+this_node
                    timer_records[sender] = int(round(time.time() * 1000))
                    #print timer_records
                    table_changed = False
                    #print "update packet is from: "+sender
                    #print json.dumps(data,indent=4)
                   #adjust to dynamic node
                    if sender not in routing_table:
                        neighbor_links[sender]=data['routing_table'][this_node]['cost']
                        routing_table[sender] = {'cost': float('inf'), 'next_hop': sender}
                        print "dynamic node "+str(routing_table[sender])

                        table_changed = True
                        
                    #add new node information
                    if routing_table[sender]['cost'] == float('inf'):
                         routing_table[sender]['cost'] = neighbor_links[sender]
                         routing_table[sender]['next_hop'] = sender
                         neighbors_table[sender] = {}
                         table_changed = True

                    # update local neighbors routing table
                    neighbors_table[sender] = data['routing_table']
                    #print "update local neighbors_table "+sender+" at "+this_node
                    for node in data['routing_table']:
                            if node != this_node:

                                # newly discovered node
                                if node not in routing_table:
                                    routing_table[node] = {'cost': float('inf'), 'next_hop': ''}
                                    print "added "+node+" at "+this_node
                                    table_changed = True                               

                                # recalculate costs/next_hop to all destinations
                                for dest in routing_table:
                                    cost = routing_table[dest]['cost']

                                    if dest in neighbors_table[sender]:
                                        new_cost = routing_table[sender]['cost'] + neighbors_table[sender][dest]['cost']
                                        if new_cost < cost:
                                            routing_table[dest]['cost'] = new_cost
                                            routing_table[dest]['next_hop'] = sender
                                            table_changed = True
                    # print 'This is the current routing table'
                    # print json.dumps(routing_table,indent=4)
                    # print 'This is the current neighbor table'
                    # print json.dumps(neighbors_table,indent=4)
                    if table_changed:
                        print 'table changed'
                        send_update()
                        table_changed = False

                elif data['command'] == 'close':
                    print "receive close"+data['close_node']+ "at "+this_node
                    timer_records[sender]=int(round(time.time()*1000))
                    close_node=data['close_node']
                    if routing_table[close_node]['cost']!=float('inf'):
                        routing_table[close_node]={'cost':float('inf'),'next_hop':''}
                       # if close_node in neighbors_table:
                        print 'set infinity '+close_node+' at '+this_node
                        if close_node in neighbors_table:

                            del neighbors_table[close_node]

                        for dest in routing_table:
                            if dest in neighbors_table:
                                routing_table[dest]={
                                'cost':neighbor_links[dest],
                                'next_hop':dest
                                }
                            else:
                                routing_table[dest]={
                                'cost':float('inf'),
                                'next_hop':''
                                }
                        packet={
                        'source':this_node,
                        'command':'close',
                        'close_node':close_node
                        }
                        for neighbor in neighbors_table:
                            neighbor_host,neighbor_port=neighbor.split(':')
                            router_socket.sendto(json.dumps(packet),(neighbor_host,int(neighbor_port)))
                    else:
                        send_update()
                ##############
                #LINK DOWN
                ##############

                elif data['command'] == 'linkdown':
                    print 'linkdown at '+str(data['link'])
                    timer_records[sender]= int(round(time.time() * 1000))
                    link_0=data['link'][0];
                    link_1=data['link'][1];
                    down_link=(link_0,link_1)
                    if down_link in link_down :
                        send_update()
                    else:

                        link_down.append(down_link)
                        if(this_node==link_1 and sender == link_0):
                            routing_table[sender]['cost']=float('inf')
                            routing_table[sender]['next_hop']=''
                            del neighbors_table[sender]

                        for dest in routing_table:

                            if dest in neighbors_table:
                                routing_table[dest]['cost'] = neighbor_links[dest]
                                routing_table[dest]['next_hop'] = dest
                            else:
                                routing_table[dest]['cost'] = float('inf')
                                routing_table[dest]['next_hop'] = ''
                        packet={
                                'command':'linkdown',
                                'link':down_link,

                            }
                        for neighbor in copy.deepcopy(neighbors_table):
                            neighbor_host, neighbor_port=neighbor.split(':')
                            router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))



                ###############
                ##LINK up
                ###############
                elif data['command'] == 'linkup':
                    print "in linkup"
                    timer_records[sender]= int(round(time.time() * 1000))
                    link_0=data['link'][0]
                    link_1=data['link'][1]
                    up_link=(link_0,link_1)
                    up_link_reverse=(link_1,link_0)
                    print up_link
                    print str(link_down)
                    if up_link in link_down:
                        print 'in linkup loop'
                        link_down.remove(up_link)
                        if(this_node==link_1 and sender==link_0):

                            routing_table[sender]['cost']=neighbor_links[sender]
                            routing_table[sender]['next_hop']=sender
                            neighbors_table[sender]={}

                        packet={
                        'command':'linkup',
                        'link':up_link
                        }
                        for neighbor in neighbors_table:
                            neighbor_host, neighbor_port = neighbor.split(':')
                            router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))
                    elif up_link_reverse in link_down:
                        link_down.remove(up_link_reverse)
                        if(this_node==link_1 and sender==link_0):
                            routing_table[sender]['cost']=neighbor_links[sender]
                            routing_table[sender]['next_hop']=sender
                            neighbors_table[sender]={}

                        packet={
                        'command':'linkup',
                        'link':up_link_reverse
                        }
                        for neighbor in neighbors_table:
                            neighbor_host, neighbor_port = neighbor.split(':')
                            router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))
                            
                    else:
                        send_update()



                ##############
                ##CHANGE COST
                ##############
                elif data['command'] == 'changecost':
                    #print 'in changecost from '+sender
                    link_0=data['link'][0]
                    link_1=data['link'][1]
                    new_cost=data['new_cost']
                    change_link=(link_0,link_1)
                    reverse_link=(link_1,link_0)
                    if(change_link in link_change_list) and (new_cost==link_change_list[change_link]):
                        send_update()
                        print "send update"
                    elif(reverse_link in link_change_list) and (new_cost==link_change_list[reverse_link]):
                        send_update()
                        print "send update"
                    else:
                        link_change_list[change_link]=new_cost
                        if(this_node==link_1):
                            neighbor_links[sender]=new_cost
                        
                        print 'in changecost loop'
                        
                        for dest in routing_table:
                            
                            if(dest in neighbors_table):               
                                routing_table[dest]['cost'] = neighbor_links[dest]
                                routing_table[dest]['next_hop'] = dest
                            else:
                                routing_table[dest]['cost'] = float('inf')
                                routing_table[dest]['next_hop'] = ''
                        packet={
                        'command':'changecost',
                        'link':data['link'],
                        'new_cost':new_cost,
                        }
                        for neighbor in neighbors_table:
                            neighbor_host, neighbor_port = neighbor.split(':')
                            router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))
                   

                ##############
                ##TRANSFER
                ##############
                elif data['command'] == 'transfer':
                    destination=data['destination']
                    if(data['destination']==this_node):
                        target_filename=data['Filename']
                        Total_num=data['Total_num']
                        #print 'sequence num'+str(data['seq_num'])
                        seq_num_list.append(data['seq_num'])
                        file_chunk=data['file_chunk'].decode('base64')
                        file_buffer.append(file_chunk)
                        
                        
                        if(len(seq_num_list)==Total_num):
                            newfilename='copy_'+data['Filename']
                            with open(newfilename,'wb') as output_file:
                                print 'create '+newfilename
                                while(file_buffer):
                                     output_file.write(file_buffer[0])
                                     file_buffer.remove(file_buffer[0])
                                seq_num_list=[]
                            
                            file_buffer=[]
                            seq_num_list=[]
                            print 'transfer successfully'
                            print "Path is "+data['path']+" -> "+this_node
                        # else:
                        #     print 'packet corruption'
                        #     seq_num_list=[]
                        #     file_buffer=[]
                        #     file_buffer=[]


                           
                                                     
                        
                    else:
                        next_hop = routing_table[destination]['next_hop']
                        next_host, next_port = next_hop.split(':')
                        new_path = data['path'] + ' -> ' + this_node
                        data['path']=new_path
                        print "Recive packet from:"+data['source']
                        print "Transmit packet to "+data['destination']
                        print "next_hop is "+next_hop
                        #print 'sequence num'+str(data['seq_num'])
                   
                        router_socket.sendto(json.dumps(data),(next_host,int(next_port)))
                        

                
            else:
                
                words = sys.stdin.readline()
                try:
                    
              
                   
                    data_split = words.strip().split(' ')
                    command = data_split[0].strip()

                    ##############
                    ##SHOWRT
                    ##############

                    if command.lower()=='showrt':
                        print json.dumps(routing_table,indent=4)
                        print json.dumps(neighbors_table,indent=4)

                        for dest in routing_table:
                            print 'dest = '+dest+', Cost= '+ str(routing_table[dest]['cost'])+', Next hop= '+routing_table[dest]['next_hop']
                    ##############
                    ##CLOSE
                    ##############                        
                    elif command.lower()=='close':
                        packet={
                        'command':'close',
                        'close_node':this_node
                        }
                        for neighbor in neighbors_table:
                            neighbor_host,neighbor_port=neighbor.split(":")
                            router_socket.sendto(json.dumps(packet),(neighbor_host,int(neighbor_port)))
                        print "Node shutdown..."
                        os._exit(1)
                    ##############
                    ##LINKDOWN
                    ##############
                    elif command.lower()=='linkdown':
                  
                        #print 'in linkdown'+str(data_split)

                        down_host=data_split[1]
                        down_port=data_split[2]

                        target_node=down_host+":"+down_port;
                        if target_node not in neighbors_table:
                            print "Error: Target node not a neighbor"
                        else:
                            link=(this_node,target_node)
                            link_down.append(link)

                            del neighbors_table[target_node]
                            print 'delete '+target_node+'in neighbors_table'
                            print json.dumps(neighbors_table,indent=4)

                            for dest in routing_table:
                                if routing_table[dest]['next_hop']==target_node:
                                    if(dest) in neighbors_table:

                                        routing_table[dest]['cost']=neighbor_links[dest]
                                        routing_table[dest]['next_hop']=dest
                                    else:
                                        routing_table[dest]['cost']=float('inf')
                                        routing_table[dest]['next_hop']=''

                            packet={
                                'command':'linkdown',
                                'link':link,

                            }

                            for neighbor in neighbors_table:
                                print json.dumps(neighbors_table,indent=4)
                                neighbor_host,neighbor_port=neighbor.split(':')
                                router_socket.sendto(json.dumps(packet),(neighbor_host,int(neighbor_port)))
                            router_socket.sendto(json.dumps(packet),(down_host,int(down_port)))


                        


                    ##############
                    ##LINKUP
                    ##############
                    elif command.lower() == 'linkup':

                        print 'in linkup'+str(data_split)
                        up_host=data_split[1]
                        up_port=data_split[2]
                        target_node=up_host+':'+str(up_port)

                        up_link=(this_node,target_node)
                        up_link_reverse=(target_node,this_node)
                        print "up_link:"+str(up_link)
                        print "current linkdown"+str(link_down)
                        if up_link in link_down:

                        
                            link_down.remove(up_link)
                            
                            routing_table[target_node]['next_hop']=target_node
                            

                            routing_table[target_node]['cost']=neighbor_links[target_node]
                            neighbors_table[target_node]={}
                            packet={
                                'command':'linkup',
                                'link':up_link
                            }
                            for neighbor in neighbors_table:
                                neighbor_host, neighbor_port = neighbor.split(':')
                                router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))
                        elif up_link_reverse in link_down:
                            
                            link_down.remove(up_link_reverse)
                            
                            routing_table[target_node]['next_hop']=target_node
                            

                            routing_table[target_node]['cost']=neighbor_links[target_node]
                            neighbors_table[target_node]={}
                            packet={
                                'command':'linkup',
                                'link':up_link
                            }
                            for neighbor in neighbors_table:
                                neighbor_host, neighbor_port = neighbor.split(':')
                                router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))                        

                        else:
                            print "not linked down before"
                        



                    ##############
                    ##CHANGECOST
                    ##############
                    elif command.lower() == 'changecost':
                        target_host=data_split[1]
                        target_port=data_split[2]
                        new_cost=float(data_split[3])
                        target_node=target_host+':'+str(target_port)
                        if target_node not in neighbors_table:
                            print "node is not neighbor"
                        else:
                            neighbor_links[target_node]=new_cost;
                            #routing_table[target_node]=new_cost
                            for dest in routing_table:
                                if dest in neighbors_table:
                                                                    
                                    routing_table[dest]['cost'] = neighbor_links[dest]
                                    routing_table[dest]['next_hop'] = dest
                                else:
                                    routing_table[dest]['cost'] = float('inf')
                                    routing_table[dest]['next_hop'] = ''
                            packet={
                            'command':'changecost',
                            'link':(this_node,target_node),
                            'new_cost':new_cost,

                            }
                            for neighbor in neighbors_table:
                                neighbor_host, neighbor_port = neighbor.split(':')
                                router_socket.sendto(json.dumps(packet), (neighbor_host,int(neighbor_port)))
                    ##############
                    ##TRANSFER
                    ##############
                    elif command.lower() == 'transfer':

                        filename=data_split[1]

                        target_host=data_split[2]
                        target_port=data_split[3]
                        target_node=target_host+':'+target_port
                        next_hop=routing_table[target_node]['next_hop']
                        next_host,next_port=next_hop.split(':')
                        path = this_node
                        sourcename="sourcefile"+"."+filename.split(".")[1]
                        with open(filename, 'rb') as f:
                            Total_num=math.ceil(sys.getsizeof(f.read())/128.0)
                        with open(filename, 'rb') as f:
                            seq_num=1;
                            seg=f.read(128)
                            file_data = base64.b64encode(seg)
                            to_send={
                            'command':'transfer',
                            'destination':target_node,
                            'file_chunk':file_data,
                            'seq_num':seq_num,
                            'path':path,
                            'source':this_node,
                            'Total_num':Total_num,
                            'Filename':sourcename
                            }
                            
                            router_socket.sendto(json.dumps(to_send),(next_host,int(next_port)))
                            while(seg):
                                seq_num=seq_num+1
                                seg=f.read(128)
                                #print "f read size is: "+str(sys.getsizeof(seg))
                                file_data = base64.b64encode(seg)
                                
                                #print seg
                                #print "file_data size is: "+str(sys.getsizeof(file_data))
                                to_send={
                                'command':'transfer',
                                'destination':target_node,
                                'file_chunk':file_data,
                                'seq_num':seq_num,
                                'path':path,
                                'source':this_node,
                                'Total_num':Total_num,
                                'Filename':sourcename
                                }
                                #frame size 188 bytes.
                                #print "Total size is: "+str(sys.getsizeof(json.dumps(to_send)))
                                router_socket.sendto(json.dumps(to_send),(next_host,int(next_port)))

                        print "File transfer successfully"

                        print "Transmit packet to "+to_send['destination']
                        print "next_hop is "+next_hop
                    else:
                        print "Input Not Valid!"
                except Exception, e:
                    print traceback.format_exc()
                    print "Error: Try again"
              
                

                            





                


