import socket
import json

socket_path = '/var/lib/nagios3/rw/live'

host_state_names = ('UP', 'DOWN', 'DOWN', 'DOWN')
service_state_names = ('OK', 'WARNING', 'CRITICAL', 'UNKNOWN')

def get(path, query, is_json=True):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(path)
    query += '\nOutputFormat: json\n' if is_json else '\n'
    print query
    s.send(query)
    s.shutdown(socket.SHUT_WR)
    data = s.recv(100000000)
    print data
    if is_json:
        return json.loads(data)
    return data


def get_hosts():
    q = '''GET hosts\nColumns: host_name host_address state state_type services_with_info'''
    data = get(socket_path, q)

    hosts = {}
    for d in data:
        name, address, state, state_type, services = d
        svcs = {}
        for service in services:
            svc_name, svc_state, svc_try, svc_info = service
            svcs[svc_name] = {
                'state': svc_state,
                'state_name': service_state_names[svc_state],
                'state_info': svc_info,
            }
        hosts[name] = {
            'address': address,
            'state': state,
            'state_name': host_state_names[state],
            'state_type': state_type,
            'services': svcs
        }

    return hosts

