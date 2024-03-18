import os
import json
import xmltodict
from tabulate import tabulate

headers = ["TestCaseName","TimeForExecution", "TestCaseID", "TestCaseDescription", "Status", "Reason"]

files = os.listdir('reports/')

def createTable(row):
  TestCaseName = row['@name']
  TimeForExecution = row['@time']
  TestCaseID = "NA"
  TestCaseDescription = "NA"
  Status = "NA"
  Reason = "Success"
  if 'failure' in row.keys():
    Status = "FAILED"
    Reason = row['failure']['@message']
  elif 'skipped' in row.keys():
    Status = "SKIPPED"
    Reason = row['skipped']['@message']
  else:
    Status = "PASS"
    if "properties" in row.keys():
      for data in row['properties']['property']:
        if data['@name'] == "test_case_id":
           TestCaseID = data['@value']
        elif data['@name'] == "test_case_description":
           TestCaseDescription = data['@value']
  table.append([TestCaseName,TimeForExecution, TestCaseID, TestCaseDescription, Status, Reason])

for file in files:
  if 'xml' in file:
    json_file = file.split('.')[0]
    with open('reports/'+file) as xml_file:
      data_dict = xmltodict.parse(xml_file.read())
    json_data = json.dumps(data_dict, indent=4, sort_keys=True)
    with open("reports/"+json_file+".json", "w") as json_file:
      json_file.write(json_data)

files = os.listdir('reports/')
for file in files:
  if 'json' in file:
     with open("reports/"+file, "r") as json_file:
        x = json.load(json_file)
        cloud = file.split('.')[0].split('-')[-1]
        tests = x['testsuite']['@tests']
        skips = x['testsuite']['@skips']
        errors = x['testsuite']['@failures']
        time = x['testsuite']['@time']
        print(isinstance(x['testsuite']['testcase'],list) )
        if not isinstance(x['testsuite']['testcase'],list):
          table = []
          createTable(x['testsuite']['testcase'])
        else:
          table =[]
          for row in x['testsuite']['testcase']:
            createTable(row)
        print("It took {} seconds to run {} tests on {}, {} tests were skipped and {} tests failed".format(time,tests,cloud,skips,errors))
        print(tabulate(table,headers, tablefmt="grid"))

