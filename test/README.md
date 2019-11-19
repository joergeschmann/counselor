# Tests

You need a running consul node for the tests. There are simple manifests for minikube in the .kube folder, or you can use the office docker image https://hub.docker.com/_/consul in case you do not already have Consul up and running.

## Docker
```ignorelang
docker run -it --rm --name consul-test -p 8500:8500 consul agent -dev -client=0.0.0.0
```

## Minikube
```ignorelang
kubectl apply -f ../.kube/consul
```
