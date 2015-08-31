Virtualization Orchestration Layer
=========================

A Virtualization Orchestration Layer: Creating/Deleting/Quering and Scheduling Virtual Machines(VMs) in a given Network.

How does it work?

Write the information of the machines in file named: machines

And also the Location of the VM image file in file name: Images

cd bin

./script ../src/machines ../src/Images


Now, by curl calls or REST calls, you can create/delete/query a VM, and also attach Storage Block devies to it by:
<h3>
Creating a VM:
</h3>

-> curl -i http://localhost:5000/vm/create?name=test\&instance_type=1\&image_id=1

<h3>
Quering a VM:
</h3>

-> curl -i http://localhost:5000/vm/query?vmid=1

<h3>
Destroy a VM:
</h3>

-> curl -i http://localhost:5000/vm/destroy?vmid=1

<h3>
List VM types:
</h3>

-> curl -i http://localhost:5000/vm/types

<h3>
List Images:
</h3>

-> curl -i http://localhost:5000/image/list

<h3>
List PMs:
</h3>

-> curl -i http://localhost:5000/pm/list

<h3>
PM Query:
</h3>

->curl -i http://localhost:5000/pm/pmid

