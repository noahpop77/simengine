"""Aggregates 3-rd party programs managed by the assets (including ipmi_sim and snmpsimd instances)
"""

import subprocess
import os
import atexit
import logging
from distutils import dir_util
import sysconfig
import pwd
import grp
import tempfile
import json
import socket
import threading
import stat
from string import Template


class StorCLIEmulator():
    
    def __init__(self, asset_key, server_dir):
        
        self._storcli_dir = os.path.join(server_dir, "storcli")
    
        os.makedirs(self._storcli_dir)
        dir_util.copy_tree(os.environ.get('SIMENGINE_STORCLI_TEMPL'), self._storcli_dir)


        self._socket_t = threading.Thread(
            target=self._listen_cmds,
            name="storcli64:{}".format(asset_key)
        )

        self._socket_t.daemon = True
        self._socket_t.start()


    def _strcli_header(self, ctrl_num=0):
        with open(os.path.join(self._storcli_dir, 'header')) as templ_h:
            options = {
                'cli_version': '007.0606.0000.0000 Mar 20, 2018',
                'op_sys': 'Linux 2.6.32-754.6.3.el6.x86_64',
                'status': 'Success',
                'description': 'None',
                'controller_line': 'Controller = {}\n'.format(ctrl_num) if ctrl_num else ''
            }

            template = Template(templ_h.read())
            return template.substitute(options)



    def _strcli_ctrlcount(self):
        with open(os.path.join(self._storcli_dir, 'adapter_count')) as templ_h:

            options = {
                'header': self._strcli_header(),
                'ctrl_count': 1
            }

            template = Template(templ_h.read())
            return template.substitute(options)

    def _strcli_ctrl_perf_mode(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'performance_mode')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
                'mode_num': 0,
                'mode_description': 'tuned to provide Best IOPS'
            }

            template = Template(templ_h.read())
            return template.substitute(options)


    def _strcli_ctrl_alarm_state(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'alarm_state')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
                'alarm_state': 'OFF'
            }

            template = Template(templ_h.read())
            return template.substitute(options)

    def _strcli_ctrl_bbu(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'bbu_data')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
                'ctrl_num': controller_num,
                'status': 'Failed',
                'property': '-',
                'err_msg': 'use /cx/cv',
                'err_code': 255
            }

            template = Template(templ_h.read())
            return template.substitute(options)


    def _strcli_bgi_rate(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'bgi_rate')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
                'bgi_rate': 30
            }

            template = Template(templ_h.read())
            return template.substitute(options)


    def _strcli_cc_rate(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'cc_rate')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
                'cc_rate': 30
            }

            template = Template(templ_h.read())
            return template.substitute(options)


    def _strcli_rebuild_rate(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'rebuild_rate')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
                'rebuild_rate': 30
            }

            template = Template(templ_h.read())
            return template.substitute(options)

    def _strcli_pr_rate(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'pr_rate')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
                'pr_rate': 20
            }

            template = Template(templ_h.read())
            return template.substitute(options)

    def _strcli_ctrl_info(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'controller_info')) as templ_h:
         
            options = {}
            template = Template(templ_h.read())
            return template.substitute(options)


    def _strcli_ctrl_cachevault(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'cachevault_data')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
            }

            template = Template(templ_h.read())
            return template.substitute(options)
        

    def _strcli_ctrl_virt_disk(self, controller_num):
        with open(os.path.join(self._storcli_dir, 'virtual_drive_data')) as templ_h:
         
            options = {
                'header': self._strcli_header(controller_num),
            }
            
            template = Template(templ_h.read())
            return template.substitute(options)
        

    def _listen_cmds(self):

        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind(('', 50000))
        serversocket.listen(5)

        conn, _ = serversocket.accept()

        with conn:
            while True:

                data = conn.recv(1024)
                if not data:
                    break
                
                received = json.loads(data) 
                argv = received['argv']

                logging.info('Data received: %s', str(received))

                reply = {"stdout": "", "stderr": "", "status": 0}

                # Process non-default return cases
                if len(argv) == 2:
                    if argv[1] == "--version":
                        reply['stdout'] = "Version 0.01"

                elif len(argv) == 3:
                    if argv[1] == "show" and argv[2] == "ctrlcount":
                        reply['stdout'] = self._strcli_ctrlcount()

                # Controller Commands
                elif len(argv) == 4 and argv[1].startswith("/c"):
                    if argv[2] == "show" and argv[3] == "perfmode":
                        reply['stdout'] = self._strcli_ctrl_perf_mode(argv[1][-1])
                    elif argv[2] == "show" and argv[3] == "bgirate":
                        reply['stdout'] = self._strcli_bgi_rate(argv[1][-1])
                    elif argv[2] == "show" and argv[3] == "ccrate":
                        reply['stdout'] = self._strcli_cc_rate(argv[1][-1])
                    elif argv[2] == "show" and argv[3] == "rebuildrate":
                        reply['stdout'] = self._strcli_rebuild_rate(argv[1][-1])
                    elif argv[2] == "show" and argv[3] == "prrate":
                        reply['stdout'] = self._strcli_pr_rate(argv[1][-1])
                    elif argv[2] == "show" and argv[3] == "all":
                        reply['stdout'] = self._strcli_ctrl_info(argv[1][-1])

                elif len(argv) == 5 and argv[1].startswith("/c"):
                    if argv[2] == "/bbu" and argv[3] == "show" and argv[4] == "all":
                        reply['stdout'] = self._strcli_ctrl_bbu(argv[1][-1])
                    elif argv[2] == "/cv" and argv[3] == "show" and argv[4] == "all":
                        reply['stdout'] = self._strcli_ctrl_cachevault(argv[1][-1])
                    elif argv[2] == "/vall" and argv[3] == "show" and argv[4] == "all":
                        reply['stdout'] = self._strcli_ctrl_virt_disk(argv[1][-1])
                elif len(argv) == 6 and argv[1].startswith("/c"):
                    if argv[2] == "/eall" and argv[3] == "/sall" and argv[4] == "show" and argv[5] == "all":
                        pass
                else:
                    reply = {"stdout": "", "stderr": "Usage: " + argv[0] +" --version", "status": 1}

                # Send the message
                conn.sendall(bytes(json.dumps(reply) +"\n", "UTF-8"))


class Agent():
    """Abstract Agent Class """
    agent_num = 1    
    

    def __init__(self):
        self._process = None


    def start_agent(self):
        """Logic for starting up the agent """
        raise NotImplementedError


    @property
    def pid(self):
        """Get agent process id"""
        return self._process.pid


    def stop_agent(self):
        """Logic for agent's termination """
        if not self._process.poll():
            self._process.kill()
    

    def register_process(self, process):
        """Set process instance
        Args:
            process(Popen): process to be managed
        """
        self._process = process
        atexit.register(self.stop_agent)
    

class IPMIAgent(Agent):
    """IPMIsim instance """

    supported_sensors = {
        'caseFan': '',
        'psuStatus': '',
        'psuVoltage': '',
        'psuPower': '',
        'psuCurrent': '',
        'psuTemperature': '',
        'memoryTemperature': '',
        'Ambient': '',
        'RAIDControllerTemperature': '',
        'cpuTemperature': ''
    }

    def __init__(self, key, ipmi_dir, ipmi_config, sensors):
        super(IPMIAgent, self).__init__()
        self._asset_key = key
        self._ipmi_dir = ipmi_dir

        # a workaround: https://stackoverflow.com/a/28055993
        # pylint: disable=W0212
        dir_util._path_created = {} 
        # pylint: enable=W0212

        dir_util.copy_tree(os.environ.get('SIMENGINE_IPMI_TEMPL'), self._ipmi_dir)

        # sensor, emu & lan configuration file paths
        lan_conf = os.path.join(self._ipmi_dir, 'lan.conf')
        ipmisim_emu = os.path.join(self._ipmi_dir, 'ipmisim1.emu')
        sdr_main = os.path.join(self._ipmi_dir, 'emu_state', 'ipmi_sim', 'ipmisim1', 'sdr.20.main')
        sensor_def = os.path.join(self._ipmi_dir, 'main.sdrs')

        lib_path = os.path.join(sysconfig.get_config_var('LIBDIR'), "simengine", 'haos_extend.so')
        
        # Template options
        lan_conf_opt = {
            'asset_key': key, 
            'extend_lib': lib_path,
            'host': ipmi_config['host'],
            'port': ipmi_config['port'],
            'user': ipmi_config['user'],
            'password': ipmi_config['password'],
            'vmport':  ipmi_config['vmport']
        }

        ipmisim_emu_opt = {
            **{
                'ipmi_dir': self._ipmi_dir, 
            },
            **IPMIAgent.supported_sensors
        }
        
        main_sdr_opt = {
            **{
                'ipmi_dir': self._ipmi_dir, 
                'includes': '',
            },
            **IPMIAgent.supported_sensors
        }

        # initialize sensors
        for i, sensor in enumerate(sensors):

            s_specs = sensor['specs']
            
            if 'index' in s_specs:
                s_idx = hex(int(sensor['address_space']['address'], 16) + s_specs['index']) 
            else:
                s_idx = s_specs['address']

            sensor_file = s_specs['name']

            index = str(s_specs['index']+1)if 'index' in s_specs else ''

            main_sdr_opt[s_specs['type']] += 'define IDX "{}" \n'.format(index)

            main_sdr_opt[s_specs['type']] += 'define ID_STR "{}" \n'.format(i)
            main_sdr_opt[s_specs['type']] += 'define ADDR "{}" \n'.format(s_idx)

            main_sdr_opt[s_specs['type']] += 'define LNR "{}"  \n'.format(s_specs['lnr'] if 'lnr' in s_specs else 0)
            main_sdr_opt[s_specs['type']] += 'define LCR "{}"  \n'.format(s_specs['lcr'] if 'lcr' in s_specs else 0)
            main_sdr_opt[s_specs['type']] += 'define LNC "{}"  \n'.format(s_specs['lnc'] if 'lnc' in s_specs else 0)
            main_sdr_opt[s_specs['type']] += 'define UNC "{}"  \n'.format(s_specs['unc'] if 'unc' in s_specs else 0)
            main_sdr_opt[s_specs['type']] += 'define UCR "{}"  \n'.format(s_specs['ucr'] if 'ucr' in s_specs else 0)
            main_sdr_opt[s_specs['type']] += 'define UNR "{}"  \n'.format(s_specs['unr'] if 'unr' in s_specs else 0)
            
            # Specify if sensor values should be returned:
            main_sdr_opt[s_specs['type']] += 'define R_LNR "{}"  \n'.format('lnr' in s_specs)
            main_sdr_opt[s_specs['type']] += 'define R_LCR "{}"  \n'.format('lcr' in s_specs)
            main_sdr_opt[s_specs['type']] += 'define R_LNC "{}"  \n'.format('lnc' in s_specs)
            main_sdr_opt[s_specs['type']] += 'define R_UNC "{}"  \n'.format('unc' in s_specs)
            main_sdr_opt[s_specs['type']] += 'define R_UCR "{}"  \n'.format('ucr' in s_specs)
            main_sdr_opt[s_specs['type']] += 'define R_UNR "{}"  \n'.format('unr' in s_specs)
            
            # s_name = s_specs['name'].format(index='"$IDX"')

            main_sdr_opt[s_specs['type']] += 'define C_NAME "{}" \n'.format(s_specs['name'])
            main_sdr_opt[s_specs['type']] += 'include "{}/{}.sdrs" \n'.format(self._ipmi_dir, s_specs['type'])

            #  0x20  0   0x74    3     1 
            e_type = s_specs['eventReadingType'] if 'eventReadingType' in s_specs else 1
            s_idx_2 = 8 if 'eventReadingType' in s_specs else 3

            ipmisim_emu_opt[s_specs['type']] += 'sensor_add 0x20  0   {}   {}     {} poll 2000 '.format(
                s_idx, s_idx_2, e_type
            )
            ipmisim_emu_opt[s_specs['type']] += 'file $TEMP_IPMI_DIR"/sensor_dir/{}" \n'.format(sensor_file)
        

        # Set server-specific includes
        if ipmi_config['num_components'] == 2:
            ipmisim_emu_opt['includes'] = 'include "{}"'.format(os.path.join(self._ipmi_dir, 'ipmisim1_psu.emu'))
            main_sdr_opt['includes'] = 'include "{}"'.format(os.path.join(self._ipmi_dir, 'main_dual_psu.sdrs'))

        # Substitute a template
        self._substitute_template_file(lan_conf, lan_conf_opt)
        self._substitute_template_file(ipmisim_emu, ipmisim_emu_opt)
        self._substitute_template_file(sensor_def, main_sdr_opt)

        # compile sensor definitions
        os.system("sdrcomp -o {} {}".format(sdr_main, sensor_def))
        subprocess.call(['chmod', '-R', 'ugo+rwx', self._ipmi_dir])
        self.start_agent()
        IPMIAgent.agent_num += 1


    def _substitute_template_file(self, filename, options):
        """Update file using python templating """
        with open(filename, "r+", encoding="utf-8") as filein:
            template = Template(filein.read())
            filein.seek(0)
            filein.write(template.substitute(options))


    def start_agent(self):
        """ Logic for starting up the agent """

        # start a new one
        lan_conf = os.path.join(self._ipmi_dir, 'lan.conf')
        ipmisim_emu = os.path.join(self._ipmi_dir, 'ipmisim1.emu')
        state_dir = os.path.join(self._ipmi_dir, 'emu_state')

        cmd = ["ipmi_sim",
               "-c", lan_conf,
               "-f", ipmisim_emu,
               "-s", state_dir,
               "-n"]

        logging.info('Starting agent: %s', ' '.join(cmd))

        self.register_process(subprocess.Popen(
            cmd, stderr=subprocess.DEVNULL, close_fds=True
        ))


    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_agent()


class SNMPAgent(Agent):
    """SNMP simulator instance """

    def __init__(self, key, host, port, public_community='public', private_community='private', lookup_oid='1.3.6'):

        super(SNMPAgent, self).__init__()
        self._key_space_id = key

        # set up community strings
        self._snmp_rec_public_fname = public_community + '.snmprec'
        self._snmp_rec_private_fname = private_community + '.snmprec'

        sys_temp = tempfile.gettempdir()
        simengine_temp = os.path.join(sys_temp, 'simengine')
        
        self._snmp_rec_dir = os.path.join(simengine_temp, str(key))
        os.makedirs(self._snmp_rec_dir)
        self._host = '{}:{}'.format(host, port)
        
        # snmpsimd.py will be run by a user 'nobody'
        uid = pwd.getpwnam("nobody").pw_uid
        gid = grp.getgrnam("nobody").gr_gid
        
        # change ownership
        os.chown(self._snmp_rec_dir, uid, gid)
        snmp_rec_public_filepath = os.path.join(self._snmp_rec_dir, self._snmp_rec_public_fname)
        snmp_rec_private_filepath = os.path.join(self._snmp_rec_dir, self._snmp_rec_private_fname)

        # get location of the lua script that will be executed by snmpsimd
        redis_script_sha = os.environ.get('SIMENGINE_SNMP_SHA')
        snmpsim_config = "{}|:redis|key-spaces-id={},evalsha={}\n".format(lookup_oid, key, redis_script_sha)

        with open(snmp_rec_public_filepath, "a") as tmp_pub, open(snmp_rec_private_filepath, "a") as tmp_priv:
            tmp_pub.write(snmpsim_config)
            tmp_priv.write(snmpsim_config)
            
        self.start_agent()

        SNMPAgent.agent_num += 1


    def start_agent(self):
        """Logic for starting up the agent """

        log_file = os.path.join(self._snmp_rec_dir, "snmpsimd.log")
        
        # start a new one
        cmd = ["snmpsimd.py", 
               "--agent-udpv4-endpoint={}".format(self._host),
               "--variation-module-options=redis:host:127.0.0.1,port:6379,db:0,key-spaces-id:"+str(self._key_space_id),
               "--data-dir="+self._snmp_rec_dir,
               "--transport-id-offset="+str(SNMPAgent.agent_num),
               "--process-user=nobody",
               "--process-group=nobody",
               # "--daemonize",
               "--logging-method=file:"+log_file
              ]

        logging.info('Starting agent: %s', ' '.join(cmd))
        self.register_process(subprocess.Popen(
            cmd, stderr=subprocess.DEVNULL, close_fds=True
        ))
