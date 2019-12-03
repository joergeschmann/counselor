# Consul up and running

## Client
The client is for simple testing. The concept of Consul is to have a client on every node that talks to the Consul cluster. The advantage is that services running on that node only need to know the local agent. 

We are not applying this concept for now. Every Consul server node runs an agent/client as well and let's you access Consul via https API. We have the Counselor lib to integrate a Consul client into our services and use the Consul service features much more flexibly.   

## Simple
The simple setup consists of just one node. There is no TLS or ACL (Access Control List) enabled. This means every one can read and write. With this simple setup, you can easily test Consul. With port-forwarding, you can access the UI at http://127.0.0.1:8500/ui.

If you want to enable ACL, you can add the following snippet to the config.yaml. There is an separate section further down on how to create policies and tokens.
```ignorelang
    "acl": {
        "enabled": true,
        "default_policy": "deny",
        "down_policy": "extend-cache",
        "tokens": {
          "master": "498073a8-5091-4e9e-871a-bbbeb030d1f6"
        }
    },
```

## Cluster
Cluster is the same as the simple setup, but with 3 nodes, to do tests with multiple nodes.

# Single node ACL
Here you have a single node with ACL enabled.

## Secure Cluster
The secure cluster also has 3 nodes and is secured with ACL and TLS enabled.

Keep in mind that it is not save to use the tokens and certificates that are added here! This is just demonstration purposes! We will move everything into Vault as soon as possible!

Unless you finish the setup, nothing is accessible. Not even the sync between the nodes.

Here are the important config entries explained:
```ignorelang
    {
        "datacenter": "dc1",
        "server": true,
        "bootstrap_expect": 3,
        "retry_join": ["consul.default.svc.cluster.local"],
        "acl": {
            "enabled": true,
            "default_policy": "deny",
            "down_policy": "extend-cache",
            "tokens": {
              "master": "498073a8-5091-4e9e-871a-bbbeb030d1f6"
            }
        },
        "client_addr": "0.0.0.0",
        "ui": true,
        "data_dir": "/consul/data",
        "encrypt": "67a5zAZfzlw8zbqhouYJA/vhT/+2g0Gan+/EkyRTUEc=",
        "verify_incoming": true,
        "verify_outgoing": true,
        "verify_server_hostname": true,
        "ca_file": "/consul/ca/consul-agent-ca.pem",
        "cert_file": "/consul/ca/node-pub.pem",
        "key_file": "/consul/ca/node-key.pem",
        "ports": {
          "http": -1,
          "https": 8501
        },
        "log_level": "INFO",
        "leave_on_terminate": true,
        "rejoin_after_leave": true
    }
```
- bootstrap_expect means that the cluster expects 3 nodes and will complain if there are more or less than that. They will elect a leader by themselves.
- retry_join tells the nodes to retry the join if the first attempt fails.
- acl enables Access Contol Lists and denies everything by default. The master token can be used to create rules, policies and tokens.
- client_addr let clients to connect from everywhere.
- encrypt defines the secret to encrypt the gossip messages between the nodes.
- verify_incoming tells Consul to check every incoming connection for a valid certificate. That means even simple curl request have to use a client certificate that is created with the certificate authority.
- verify_outgoing forces Consul to only serve requests when the connection is secured with TLS.
- verify_server_hostname instructs Consul to check whether the hostname matches with with name specified in the certificate.
- ca_file is the public key of the authority certificate. It can verify all the certificates.
- cert_file is the public part of the node's certificate.
- key_file is the private part of the node's certificate.
- ports deactivates the http port and activates https on port 8501

More information is accessible in the official documentation https://www.consul.io/docs/agent/options.html.

To complete the setup there are additional steps necessary. For simplicity, you can deactivate verify_incoming, so you do not have to use the client certificate for every request you send to the Consul cluster.

### Create certificates
The official tutorial for creating certificates is here: https://learn.hashicorp.com/consul/security-networking/certificates

Create the authority certificate
```ignorelang
consul tls ca create
``` 

Create server certificates
```ignorelang
consul tls cert create -server
```

Creating client certificates
```ignorelang
consul tls cert create -client
```
To automatically distribute the client certificates, there is also a configuration called auto_encrypt.

If you need to import a client certificate into you browser to be able to open the Consul UI, you need to convert the certificate pem files into a pkcs12 file:
```ignorelang
openssl pkcs12 -export -inkey client-key.pem -in client-pub.pem -out clientKeyStore.p12
``` 

### Creating policies and Tokens

#### Write token for every node to sync itself
Depending on what security features you have activated, you can create a write policy for the node consul-0 with the name consul-0 for a specific node this way:
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Name":"consul-0","Description":"","Rules":"node \"consul-0\" { policy = \"write\"}"}' https://127.0.0.1:8501/v1/acl/policy -v
```
- -k is the insecure flag to trust the self signed certificate.
- --cert tells which client certificate to use
- X-Consul-Token adds the master token for the ACL check

To create a token with the name consul-0-token of the above policy you can use this request:
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Name":"consul-0-token","Description":"consul 0 token","Policies":[{"Name":"consul-0"}]}' https://127.0.0.1:8501/v1/acl/token -v
```
You will receive a SecretId uuid token like '90a70a8a-faac-b61c-c253-823f3f362da7' that you can assign to the consul-0 node.

To reach the consul-0 node you can forward the port:
```ignorelang
kubectl port-forward pod/consul-0 38501:8501
```

And set the token:
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Token": "90a70a8a-faac-b61c-c253-823f3f362da7"}' https://127.0.0.1:38501/v1/agent/token/agent -v
```

You need to repeat these steps for every node in the cluster. Once done, all nodes are able to sync.

#### Token to register services
To create a policy to register a specific service, create a policy with write access:
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Name":"test-service","Description":"","Rules":"service \"test-service\" { policy = \"write\" }"}' https://127.0.0.1:8501/v1/acl/policy -v
```
And a token as well:
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Name":"test-service-token","Description":"test service token","Policies":[{"Name":"test-service"}]}' https://127.0.0.1:8501/v1/acl/token -v
```
You also get a SecretId uuid token like '00fc29a2-53df-14bf-086f-91621fe9d290' that you can use as the header token (X-Consul-Token) in your requests.

```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 00fc29a2-53df-14bf-086f-91621fe9d290" -d '{"ID":"test-service","Name":"test-service","Kind":"test-service","Tags":["primary","test","v1.1"],"Meta":{"version":"1.0"},"EnableTagOverride":true}' https://127.0.0.1:8501/v1/agent/service/register?replace-existing-checks=1 -v
```

If you try to register a service with the name test-service-1, you get a 403 - Permission denied.

Write access also means read access:
```ignorelang
curl -k --cert certificates.pem -X GET -H "X-Consul-Token: 00fc29a2-53df-14bf-086f-91621fe9d290" https://127.0.0.1:8501/v1/agent/service/test-service -v
```

#### Token to write Key Value entries
Let us create a policy for a service:
```ignorelang
{
  "Name": "test-app-policy",
  "Description": "Allow test app to read all but only write to config",
  "Rules": "key_prefix \"test/app/\" { policy = \"read\" } key \"test/app/config\" { policy = \"write\" }"
}
```
It allows to read the /test/app entries, but allow writes only to the sub path /test/app/config
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Name":"test-app-policy","Description":"Allow test app to read all but only write to config","Rules":"key_prefix \"test/app/\" { policy = \"read\" } key \"test/app/config\" { policy = \"write\" }"}' https://127.0.0.1:8501/v1/acl/policy -v
```
We get the token with:
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Name":"test-app-token","Description":"test app token","Policies":[{"Name":"test-app-policy"}]}' https://127.0.0.1:8501/v1/acl/token -v
```
We can now write to /test/app/config with the received SecretID:
```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 94a3199e-de27-5426-c4cd-e2fd4c8f0c0e" -d '{"key1":"value1", "key2":true, "key3": 3.1415}' -H "Content-Type: application/json" https://127.0.0.1:8501/v1/kv/test/app/config
```
If the request was successful you should get True as response.
```ignorelang
curl -k --cert certificates.pem -X GET -H "X-Consul-Token: 94a3199e-de27-5426-c4cd-e2fd4c8f0c0e" https://127.0.0.1:8501/v1/kv/test/app?recurse=true -v
```
The entries are then returned as array of entries:
```ignorelang
[
  {
    "LockIndex": 0,
    "Key": "test/app/additions",
    "Flags": 0,
    "Value": "ewogInF1ZXN0aW9uIjogNDIgCn0=",
    "CreateIndex": 42400,
    "ModifyIndex": 42400
  },
  {
    "LockIndex": 0,
    "Key": "test/app/config",
    "Flags": 0,
    "Value": "eyJrZXkxIjoidmFsdWUxIiwgImtleTIiOnRydWUsICJrZXkzIjogMy4xNDE1fQ==",
    "CreateIndex": 42373,
    "ModifyIndex": 42373
  }
]
```
As you see, the actual config is encoded as base64 string in the Value field:
```ignorelang
echo "eyJrZXkxIjoidmFsdWUxIiwgImtleTIiOnRydWUsICJrZXkzIjogMy4xNDE1fQ==" | base64 -d
{"key1":"value1", "key2":true, "key3": 3.1415}(
```

#### Token for the Consul UI
The token for the UI is a bit different, because you need access to multiple resources.
```ignorelang
{
  "Name": "UI Token",
  "Type": "client",
  "Rules": "key \"\" { policy = \"read\" } node \"\" { policy = \"read\" } service \"\" { policy = \"deny\" }"
}
```
In this example we give read access to all keys, nodes and services. We could restrict the access with prefixes like node_prefix "test-nodes", service_prefix "test-service" or key_prefix "test/", though.

```ignorelang
curl -k --cert certificates.pem -X PUT -H "X-Consul-Token: 498073a8-5091-4e9e-871a-bbbeb030d1f6" -d '{"Name":"UI Token","Type":"client","Rules":"key \"\" { policy = \"read\" } node \"\" { policy = \"read\" } service \"\" { policy = \"deny\" }"}' https://127.0.0.1:8501/v1/acl/create -v
```
You can enter the ID you get, like 01f72861-d2c9-05f7-28d2-5aecad7f0c00, on the UI itself and should then be able to see all nodes, services and KV entries. 