AzureML (AML) v2 command job template.

1) Install AML CLI:
   az extension add -n ml

2) Set defaults:
   az configure --defaults group=<RG> workspace=<WS> location=<REGION>

3) Edit compute cluster name:
   azureml/command_job.yaml -> compute: azureml:<cluster_name>

4) Submit:
   az ml job create -f azureml/command_job.yaml
