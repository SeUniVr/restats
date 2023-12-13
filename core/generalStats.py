import utils.parsers as parsers
import utils.dbmanager as dbm

import os.path
import re
import json



dest = None


def writeGeneralStats(dbfile, confDict):
    """
    Parsing num of operations
    """

    dbm.create_connection(dbfile)

    res = dbm.getOperationTested()

    operations = []
    for single in res:
        operation = single[1] + " " + single[0]
        operations.append(operation)


    log_file = confDict['logFile']
    raw_errors = dbm.getAllErrors()

    with open(log_file, "r") as f:
        requests_and_responses = f.read().split("========REQUEST========\n")
        for request_and_response in requests_and_responses:
            if "RESPONSE" in request_and_response:
                log_request = request_and_response.split("========RESPONSE========\n")[0]
                log_response = request_and_response.split("========RESPONSE========\n")[1]
                currentPath = os.path.dirname(log_file)
                temp_request_file = currentPath + "/tempRequest.txt"
                temp_response_file = currentPath + "/tempResponse.txt"
                with open(temp_request_file, "w") as req_file:
                    req_file.write(log_request)
                with open(temp_response_file, "w") as res_file:
                    res_file.write(log_response)
                # Parse request
                request = parsers.RawHTTPRequest2Dict(temp_request_file)
                # Parse response
                response = parsers.RawHTTPResponse2Dict(temp_response_file)

                if 200 <= int(response['status']) < 300:
                    successfulCount += 1
                elif 400 <= int(response['status']) < 500:
                    clientErrorCount += 1
                elif int(response['status']) >= 500:
                    serverErrorCount += 1
                    response_text = response['body']
                    if "stackTrace" in response_text:
                        response_text = response_text[response_text.find('"stackTrace"'):]
                        response_text = response_text[:response_text.find('java.lang.Thread')]
                        response_text = response_text[:response_text.find('Thread.java')]
                    elif "<title>" in response_text:
                        response_text = response_text[response_text.find("<title>"):response_text.find("</title>")]
                    elif "java:" in response_text:
                        response_text = re.findall(r"\w+\.java:\d+", response_text)
                        response_text = ', '.join(response_text)
                    else:
                        response_text = response_text[response_text.find("Error:"):]
                        response_text = re.sub(r'\[.*?\]', '', response_text)  # Remove words in square brackets
                        response_text = re.sub(r'\(.*?\)', '', response_text)  # Remove words in round brackets
                        response_text = re.sub(r'\'(.*?)\'|"(\1)"', '',
                                               response_text)  # Remove words in single or double quotes

                    error_message = response_text.strip()
                    unique_stack_traces[error_message] += 1


    """
    Parsing unique error
    """
    unique_5xx_count = 0
    errors = []
    for stack_trace, count in unique_stack_traces.items():
        error = {"stack_trace": stack_trace, "count": count}
        unique_5xx_count += 1
        errors.append(error)






    with open(dest + '/generalStats.json', 'w+') as out:
        json.dump({
                    "numOperationCovered": len(operations),
                   "Operation covered": operations,
                    "numErrors": unique_5xx_count,
                    "Errors": errors,
                    "numberOfInteraction": {
                        "total" : successfulCount + clientErrorCount + serverErrorCount,
                        "2XX" : successfulCount,
                        "4XX" : clientErrorCount,
                        "5XX" : serverErrorCount
                    }
                   },
                  out,
                  indent='\t')

    dbm.close()


def generateGeneralStats(specDict, confDict):
    global dest

    dest = confDict['reportsDir']
    # temp fix
    if dest[-1] != '/':
        dest = dest + '/'
    dbfile = confDict['dbPath']
    writeGeneralStats(dbfile, confDict)





