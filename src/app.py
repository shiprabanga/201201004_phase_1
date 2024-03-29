#!flask/bin/python
from flask import Flask, jsonify,abort,request
import libvirt
import json
import copy
import os, sys
import subprocess

app = Flask(__name__)
img = []
vm_img = []
pms = []
pm_id_list = []
vms = {}
pm_chosen_dict = {}
vm_ids_list=[]
VM_TYPES_FILE = "VM_types"
Initial_Machine_Config = {}
Machine_Specs = {}
fifo_ctr = 1

M_id = 1
f = open("machines" ,"r")
for machine in f:
	machine = machine.strip('\n')
	machine = machine.strip("\r")

        
	os.system(" ssh " + machine +" free -k | grep 'Mem:' | awk '{ print $4 }' >> data")
	os.system(" ssh " + machine +" grep processor /proc/cpuinfo | wc -l >> data") 
	fin = open("data","r")
	M_ram = fin.readline().strip('\n')
        M_cpu = fin.readline().strip('\n')
	fin.close()
	os.system("rm -rf data")

	temp_dict = {}
	temp_dict['ip'] = machine
	temp_dict['ram'] = M_ram
	temp_dict['cpu'] = M_cpu
	Machine_Specs[M_id] = temp_dict
	M_id += 1
f.close()
Initial_Machine_Config = copy.deepcopy(Machine_Specs)

@app.route('/vm/query', methods=['GET'])
def get_vms():
    args = request.args
    vmid = args['vmid']
    print "************" + pm_chosen_dict[str(vmid)]+"/system"
    conn = libvirt.open("qemu+ssh://"+pm_chosen_dict[str(vmid)]+"/system")
    dom = conn.lookupByName(vms[vmid]['name'].strip('\r'))
    infos = dom.info()
    if infos[1] == 512000:
            it = 1
    elif infos[1] == 1024000:
            it = 2
    elif infos[1] == 2048000:
            it = 3
    return jsonify(vmid = vmid,
            name = vms[vmid]['name'],
            instance_type = str(it),
            pmid = vms[vmid]['pmid'])

@app.route('/vm/create', methods=['GET'])
def create_vm():
    args = request.args
    name = str(args['name'])
    instance_type = int(args['instance_type'])
    image_id = int(args['image_id'])
    vm_detail = get_vm_types(instance_type)

    vm_cpu = vm_detail['cpu']
    vm_ram = vm_detail['ram']
    vm_disk = vm_detail['disk']
    global image_name

    for vm in vm_img:
        if vm['id'] == image_id:
            image_name = vm['name']

    global pm_chosen
    pm_chosen_id = Scheduler(vm_ram, vm_cpu)
    pm_chosen = pms[pm_chosen_id]['name']
    user = pm_chosen.split("@")[0]
    send_image(pm_chosen, image_name)

    if len(vm_ids_list) == 0:
        i=1
        vm_ids_list.append(i)
    else:
        i = int(vm_ids_list[-1])+1
        vm_ids_list.append(i)

    vmid = i
    pm_chosen_dict[str(vmid)] = pm_chosen
    vms[str(vmid)] = {}
    vms[str(vmid)]['name'] = name
    vms[str(vmid)]['pmid'] = pm_chosen_id
    imagePath = image_name.split(':')[1]
    xml = """<domain type='qemu' id='%s'><name>%s</name><memory>%s</memory>            <currentMemory>512000</currentMemory>            <vcpu>%s</vcpu>            <os>            <type arch='i686' machine='pc-1.0-precise'>hvm</type>            <boot dev='hd'/>            </os>        <features>            <acpi/>            <apic/>            <pae/>        </features>        <clock offset='utc'/>  <on_poweroff>destroy</on_poweroff>  <on_reboot>restart</on_reboot>  <on_crash>restart</on_crash>  <devices>    <emulator>/usr/bin/qemu-system-i386</emulator>    <disk type='file' device='disk'>      <driver name='qemu' type='qcow2'/>      <source file='%s' />      <target dev='hda' bus='ide'/>      <alias name='ide0-0-0'/>      <address type='drive' controller='0' bus='0' unit='0'/>    </disk>    <controller type='ide' index='0'>      <alias name='ide0'/>      <address type='pci' domain='0x0000' bus='0x00' slot='0x01' function='0x1'/>    </controller>    <interface type='network'>      <mac address='52:54:00:82:f7:43'/>      <source network='default'/>      <target dev='vnet0'/>      <alias name='net0'/>      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>    </interface>    <serial type='pty'>      <source path='/dev/pts/2'/>      <target port='0'/>      <alias name='serial0'/>    </serial>    <console type='pty' tty='/dev/pts/2'>      <source path='/dev/pts/2'/>      <target type='serial' port='0'/>      <alias name='serial0'/>    </console>    <input type='mouse' bus='ps2'/>    <graphics type='vnc' port='5900' autoport='yes'/>    <sound model='ich6'>      <alias name='sound0'/>      <address type='pci' domain='0x0000' bus='0x00' slot='0x04' function='0x0'/>    </sound>    <video>      <model type='cirrus' vram='9216' heads='1'/>      <alias name='video0'/>      <address type='pci' domain='0x0000' bus='0x00' slot='0x02' function='0x0'/>    </video>    <memballoon model='virtio'>      <alias name='balloon0'/>      <address type='pci' domain='0x0000' bus='0x00' slot='0x05' function='0x0'/>    </memballoon>  </devices>  <seclabel type='dynamic' model='apparmor' relabel='yes'>    <label>libvirt-10a963ef-9458-c30d-eca3-891efd2d5817</label>    <imagelabel>libvirt-10a963ef-9458-c30d-eca3-891efd2d5817</imagelabel> </seclabel></domain>""" % (i, name, str(int(vm_ram)*1000), str(vm_cpu), str(imagePath))

    try:
        print "qemu+ssh://"+pm_chosen_dict[str(vmid)]+"/system"
        conn = libvirt.open("qemu+ssh://"+pm_chosen_dict[str(vmid)]+"/system")
        conn.defineXML(xml)
        dom = conn.lookupByName(name)
        dom.create()
        result = "{\n%s\n}" %str(vmid)
        conn.close()
        return jsonify({'vmid': vmid }), 201
    except:
        return jsonify(status=0)

def send_image(pm, image_path):
    image_path = image_path.strip("\r")
    if pm == image_path.split(":")[0]:
        return
    os.system("ssh " + pm + " rm /home/"+pm.split("@")[0]+"/"+image_path.split("/")[-1])
    bash_command = "scp " + image_path + " " + pm + ":/home/" + pm.split("@")[0] + "/"
    os.system(bash_command)

@app.route('/vm/destroy', methods=['GET'])
def destroy_vm():
    args = request.args
    vmid = args['vmid']
    conn = libvirt.open("qemu+ssh://"+pm_chosen_dict[str(vmid)]+"/system")
    dom = conn.lookupByName(vms[vmid]['name'])
    try:
        dom.destroy()
        conn.close()
        return jsonify(status=1)
    except:
        return jsonify(status=0)

@app.route('/image/list', methods=['GET'])
def list_images():
    json_ret = '{\n"images":['
    for vm in vm_img:
        json_ret += "{"
        for key in vm.keys()[:1]:
            json_ret += '"%s":"%s",'%(key,vm[key])
        key = vm.keys()[-1]
        json_ret += '"%s":"%s"}'%(key,vm[key])
    json_ret +="]\n}\n"
    return json_ret

@app.route('/vm/types', methods=['GET'])
def list_vmtypes():
    f = open("VM_types", "r")
    l = f.read()
    return l

@app.route('/pm/list', methods=['GET'])
def list_pms():
   json_ret = '{\n"pms":['
   for pm in pms:
       json_ret += str(pm['id']) + ','
   json_ret +="]\n}\n"
   return json_ret

@app.route('/pm/<int:pmid>/listvms', methods=['GET'])
def vm_list(pmid):
    global vms
    vmids = []
    for vm in vms:
        print "*****" + vm
        if vm["pmid"] == pmid:
            vmids.append(vm['vmid'])
    return jsonify(vmids = vmids)

@app.route("/pm/<int:pmid>", methods = ['GET'])
def pm_details(pmid):
	global Machine_Specs
	global Initial_Machine_Config
	ToReturn = {}
	ToReturn['pmid'] = pmid
	ToReturn['capacity'] = Initial_Machine_Config[pmid]
	ToReturn['free'] = Machine_Specs[pmid]

	VM_count = 0
	VMs = list(vms.values())
	for VM in VMs:
		if VM['pmid'] == pmid:
			VM_count += 1
	ToReturn['vms'] = VM_count
	return jsonify(ToReturn)

def update_PM_list():
    pms_det = []
    global pms
    f = open(sys.argv[1], "r")
    for i in f.readlines():
        i = i.strip('\r')
        pms_det.append(i.strip('\n'))
    for pm in pms_det:
        temp = {}
        temp['id'] = len(pms)+1
        temp['name'] = pm
        pms.append(temp)


def make_image_list():
    f = open(sys.argv[2], "r")
    for i in f.readlines():
        i=i.strip("\r")
        img.append(i.strip("\n"))

    for image in img:
        temp = {}
        temp['id']= len(vm_img)+1
        temp['name']=image
        vm_img.append(temp)

def get_vm_types(tid = None):
    f=open(VM_TYPES_FILE, "r")
    val = json.loads(f.read())['types']
    if tid!=None:
        for i in val:
            if i['tid'] == tid:
                return i
    else:
        return val
    return 0

def Scheduler(ram, cpu):
	global Machine_Specs
	global fifo_ctr
	temp_ctr = fifo_ctr

	while(True):
		if Machine_Specs[fifo_ctr]['ram'] >= ram and Machine_Specs[fifo_ctr]['cpu'] >= cpu:
			Machine_Specs[fifo_ctr]['ram'] = ram
			Machine_Specs[fifo_ctr]['cpu'] = cpu
			return fifo_ctr
		fifo_ctr = ((fifo_ctr)%(len(Machine_Specs)))+1
		if fifo_ctr == temp_ctr:
			return 0

if __name__ == '__main__':
    make_image_list()
    update_PM_list()
    app.run(debug=True)
