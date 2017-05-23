import json
import logging
import re
import socket
import subprocess
import time

import colorlog

logger = logging.getLogger(__name__)


# VALID_HOSTNAME = re.compile('^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$')
VALID_HOSTNAME = re.compile('')


class NonZeroExitCode(Exception):
    pass


def _run_call(*args):
    logger.debug(f'Running command: {args!r}')
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    stdout, _ = proc.communicate()
    if proc.returncode != 0:
        raise NonZeroExitCode('Command {!r} returned a non-zero exit '
                              'code of {}'.format(args, proc.returncode))
    return stdout.decode()


class Docker(object):
    def __init__(self):
        self._current_container_info = None

    def list_container_names(self, network=None):
        command = ['docker', 'ps', '--format', '{{.Names}}']
        if network is not None:
            command.extend(['--filter', f'network={network}'])
        output = _run_call(*command)
        container_names = output.split()
        return container_names

    def inspect_container(self, container_name):
        container_json = _run_call('docker', 'inspect', container_name)
        info = json.loads(container_json)
        assert len(info) == 1
        return info[0]

    @property
    def current_container_info(self):
        if self._current_container_info is None:
            hostname = socket.gethostname()
            self._current_container_info = self.inspect_container(hostname)
        return self._current_container_info

    @property
    def current_network(self):
        info = self.current_container_info
        networks = list(info['NetworkSettings']['Networks'].keys())
        if len(networks) > 1:
            logger.warning('Container has more than one network '
                           f'({networks!r}')
        return networks[0]

    @property
    def current_container_name(self):
        return self.current_container_info['Name'].strip('/')


class Nginx(object):
    config_path = '/etc/nginx/conf.d/default.conf'

    def get_config(self):
        with open(self.config_path) as f:
            return f.read()

    def set_config(self, config):
        with open(self.config_path, 'w') as f:
            return f.write(config)

    def reload(self):
        logger.info('Reloading nginx')
        _run_call('nginx', '-s', 'reload')

    def verify_config(self):
        try:
            _run_call('nginx', '-t')
        except NonZeroExitCode:
            logger.debug('Nginx config NOT OK')
            return False
        else:
            logger.debug('Nginx config OK')
            return True

    @staticmethod
    def make_server_block(hostname, port=80):
        return """
            server {
              listen 80;
              server_name %(hostname)s;
                location / {
                  access_log off;
                  proxy_pass http://%(hostname)s:%(port)d;
                  proxy_set_header X-Real-IP $remote_addr;
                  proxy_set_header Host $host;
                  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                }
            }
            """ % {'hostname': hostname, 'port': port}


def generate_config():
    docker = Docker()
    current_network = docker.current_network
    current_container_name = docker.current_container_name
    if current_network == 'bridge':
        raise Exception("You need to run this container with it's own network "
            "using '--network=network_name. You will need to create a network "
            "first with 'docker network create network_name'")
        return
    logger.debug(f'Current newtwork is {current_network!r}')
    container_names = docker.list_container_names(network=current_network)
    try:
        container_names.remove(current_container_name)
    except ValueError:
        logger.warning(f"This container's name ({current_container_name!r}) "
                       f"was not found on network {current_network!r}")
    logger.info(f'Found containers: {container_names!r}')
    # Sort the names to make the config reproducible
    container_names.sort()
    blocks = map(Nginx.make_server_block, container_names)
    config = '\n\n'.join(blocks)
    return config


def update_config():
    nginx = Nginx()
    config = generate_config()
    old_config = nginx.get_config()
    if config == old_config:
        logger.info('Old configuration and new configuration match,'
                    ' not updating')
        return  # Nothing to do here
    nginx.set_config(config)
    if nginx.verify_config():
        nginx.reload()
        logger.info('Nginx configuration successfully updated')
        logger.debug(f'New config is:\n {config}')
    else:
        logger.error('Invalid nginx configuration. Rolling back config...')
        nginx.set_config(old_config)


def main():
    sleep_interval = 20
    while True:
        logger.debug('Starting config update...')
        t_start = time.time()
        try:
            update_config()
        except Exception:
            logger.exception('Exception while updating config:')
        delta_t = time.time() - t_start
        logger.debug(f'Updated config in {delta_t:.1f} seconds')
        logger.info(f'Sleeping for {sleep_interval:d} seconds...')
        time.sleep(sleep_interval)


if __name__ == '__main__':
    handler = colorlog.StreamHandler()
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level=logging.DEBUG)
    # logging.basicConfig(level=logging.DEBUG)
    main()
    # d = Docker()
    # from pprint import pprint
    # pprint(d.list_container_names())
    # pprint(d.get_container_info('nginx'))
