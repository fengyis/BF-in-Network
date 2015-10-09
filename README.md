#Bellman-Ford Algorithm in Computer Network
##Description:

In this assignment  I will implement a version of the distributed Bellman­Ford algorithm. The algorithm will operate using a set of distributed host processes. The hosts perform the distributed distance computation and support a command line user interface, e.g. each host allows the user to edit links to the neighbors and view the routing table. Hosts may be distributed across different machines and more than one host can be on the same machine.
Part 1.
​In this part, I implement the BellmanFord Algorithm by maintaining a correct routing table in the presence of link cost changes, failures and link up. In addition, in order to avoid "count to infinity" problem, I also implement poison reverse in routing optimization. 

Each host has a config file to start up with, which specifies its neighbors by default. Each time a host starts up, it assumes that its neighbors are already connected. If not, the host will disconnect to it by the detection of time out events. In addition, I use UDP socket in sending and receiving packets from other hosts. 

Basically, I constructed three threads in my program. One is the main thread which listen to the connection from other hosts as well as the input from user at application layer. Whenever a socket or system I/O's status changes, it will be pushed into a queue waiting to be processced.  The second is to send current routing table periodicly. The last thread is to periodicly check whether neighbors are lost or not and such period is defined in the config file. 

In the main thread, there are simply two scenarioes to be considered. One is processing the packets sent from its neigbors and the other is to process the command taken from application layer. In terms of packets processing, the possible command is update, close, linkdown, linkup, changecost and transfer. Each corresponds to the operation required in the specification. This is also true for the application level with small difference in the way of wrapping up packets. 


##Operation Instruction:
**1. Initialization/ Host Startup**
```
$ python bfclient.py clientX.txt
```
clientX.txt is the local configure file where it specifies the local port number, neighbors, timeout and costs.

##Functionality 	

**1.Linkdown**
```
$ linkdown IPaddress PortNumber
```
IPaddress and PortNumber are the target node destination address and have to exist in the neighbors' list. 

**2.Linkup**
```
$ linkup IPaddress PortNumber
```
IPaddress and PortNumber are the target node destination address and such link has to be linked down before otherwise it will not work.

**3. Changecost**
```
$ changecost IPaddress PortNumber newcost
```
IPaddress and PortNumber are the target node destination address and the newcost is the cost that you want to change to. 

**4. Transfer**
```
$ trasnfer filename IPaddress PortNumber
```
The size of header is 194 bytes and this size might vary slightly because of the type of the file. I set the size of data that the program read each time as 128 bytes. After converting to binary bytes, the total size of data is 209 bytes. Therefore, the total bytes of each packet is about 194+209=403 (bytes). Therefore, I set the MSS of each packet as 512 bytes as maximum. In order to keep the file size controllable as far as we can, I rename the input file as "sourcefile" while keep the file extention as same. The name of output file is set as "copy_sourcefile" with same extention. Note that file is assumed to be in the same directory as bfclient.py

**5. close**
```
$ close
```
This will shutdown current node. Other nodes will detect this and then delete its information in their routing table.


