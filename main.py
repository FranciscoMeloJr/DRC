import yaml
import sys
print (sys.argv)
print(sys.version)

def main():
  print('CRD reader/parser')
  if (len(sys.argv)<2):
    print('Enter the file path')
  else:
    print('Reading file' + sys.argv[1])
    file_name = "lib/infinispan.yaml" #sys.argv[1]
    data = read_yaml(file_name)
    read_crd(data)
    
def read_yaml(file_name, debug=False):
    with open(file_name, "r") as stream:
        try:
          data = yaml.safe_load(stream)
          if debug:
            print(data)
        except yaml.YAMLError as exc:
            print(exc)
    return data

def read_crd(data, debug_flag = False):
  if debug_flag:
    for each_element in data:
      print(each_element)

  print('=============== Kind ==================')
  print(data['kind'])
  
  print('=============== Metadata ===============')
  print(data['metadata'])
  
  print('=============== Spec ===============')
  print(data['spec'])
  replicas =  data['spec']['replicas']
  type = data['spec']['service']['type']
  print(type)
  print('Number of the replicas: ' + str(replicas))
  if type == 'Cache':
    print('Deprecated service type == use DataGrid')
  print('=============== Status ============= ')
  print(data['status'])

main()

