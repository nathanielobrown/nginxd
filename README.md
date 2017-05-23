# nginxd
nginxd is the fastest way to setup service discovery and [virtual hosts](https://en.wikipedia.org/wiki/Virtual_hosting) on a single docker machine. It allows you to add and remove dockerized webapps without manually updating your nginx configuration.

## Usage
1. Create a docker network: `docker network create nginxd`
2. Run nginxd on that network: `docker run -it -v /var/run/docker.sock:/var/run/docker.sock --network=nginxd -p 80:80 nathanielobrown/nginxd`
3. Run some other containers on the same network with port 80 exposed and names that correspond to the external domains you want routed to them: `docker run -it --expose 80 --network nginxd --name mydomain.com tutum/hello-world`
4. Make sure your domain (`mydomain.com` in the example) is pointing to your docker machine. If you are testing locally, you can set `mydomain.com` to 127.0.0.1 in your [hosts](https://support.rackspace.com/how-to/modify-your-hosts-file/) file.
5. Head to `mydomain.com` and voila! If you add another container with a different name, nginx will route requests to that container as well.

## How it works
By bind mounting the docker socket (`/var/run/docker.sock`) into nginxd we give the container full control over docker. Every 20 seconds, a Python script inside the nginxd container uses docker to list the containers running on the same network. If the script finds that a container has been added or removed, it updates the nginx configuration accordingly. Requests are routed based on requested hostname, and hostname is determined by docker container name. So if you launch a container named `mydomain.com` all requests to `mydomain.com` will be routed to that container.

## Security
Bind mounting the docker socket is a little dangerous because if someone gains access to the container, they gain full access to all of your docker hosts. I'm not a security expert, but I think this particalarly scenario is relatively safe because we are only exposing nginx, which is pretty battle-hardened.