import re
import json

from collections import Counter

import utils.parsers as parsers
import utils.dbmanager as dbm

def generatePairs(confDict, pathsInSpec, basesInSpec):
	log_file = confDict['logFile']
	#dest = confDict['pairsDir']
	dbFile = confDict['dbPath']

	'''
	Sorting paths in the specification to try to avoid path collision:
	"/user/{id}" and "/user/auth" have a collision because the second
	can be matched by the regex of the first. With a sorted list, the order is
	inverted, so the first regex matching should be the right one.
	'''
	pathsInSpec.sort()

	'''
	Have to be sure that every resource from every possible server is taken
	in consideration.
	'''
	regPaths = []
	for i in range(len(pathsInSpec)):

		suffix = ''
		actualPath = pathsInSpec[i]
		actualPath = actualPath.replace('*', '.*')
		#print('path:', pathsInSpec[i], 'actualPath:', actualPath)

		for b in basesInSpec:
			suffix = suffix + '(' + b.replace('/', '/') + ')|'

		regPaths.append('(' + suffix[:-1] + ')' + actualPath)

	'''
	From every path in the specification extract a regular expression
	for pattern matching with the actual paths found in the requests.
	'''
	paths_re = [re.sub('\{{1}[^{}}]*\}{1}', '[^/]+', x) for x in regPaths]
	paths_re = [x + '?$' if x[-1] == '/' else x + '/?$' for x in paths_re]
	paths_re = [re.compile(x) for x in paths_re]

	unmatched = [] # unmatched requests/responses
	pair_number = 0 # previous file number
	pair = {} # pair map for easy json writing

	#####################
	#### POPULATE DB ####
	dbm.create_connection(dbFile)
	dbm.createTables()
	####     END     ####
	#####################

	unique_stack_traces = Counter()
	successfulCount = 0
	clientErrorCount = 0
	serverErrorCount = 0
	counter = 0
	# Gets every entry in the directory, and keeps only files
	with open(log_file, "rb") as f:
		requests_and_responses = str(f.read(), 'UTF-8').split("========REQUEST========\n")
		for request_and_response in requests_and_responses:
			counter +=1
			if counter % 100 == 0:
				print("interaction num "+ str(counter))
			if "RESPONSE" in request_and_response:
				log_request = request_and_response.split("========RESPONSE=========\n")[0]
				log_response = request_and_response.split("========RESPONSE========\n")[1]
				# Parse request
				request = parsers.RawHTTPRequest2Dict(log_request)
				pair['pairNumber'] = pair_number

				# To check if a path matches one in the spec
				match = False
				# print('actual path: ', request['path'])

				# replace the path extracted from the request with the specification matching one
				for (r, path) in zip(paths_re, pathsInSpec):
					# print('re:', r, 'path:', path)

					if (r.match(request['path'])):
						match = True
						request['path'] = path
						break

				# x = input()
				pair['request'] = request

				# Parse response
				response = parsers.RawHTTPResponse2Dict(log_response)
				pair['response'] = response

				if 200 <= int(pair['response']['status']) < 300:
					successfulCount += 1
				elif 400 <= int(pair['response']['status']) < 500:
					clientErrorCount += 1
				elif int(pair['response']['status']) >= 500:
					serverErrorCount += 1
					response_text = pair['response']['body']
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

				# parsers.pair2json(pair, prev_number, dest)
				# If there is no match with the API specification paths
				# The path is ignored and not counted in the statistics.
				if not match:
					print("No Matching")
					unmatched.append(pair['request']['path'])
					pair_number += 1
					pair.clear()
					continue

				#####################
				#### POPULATE DB ####

				pathID = dbm.getPathID(pair['request']['path'])
				method = pair['request']['method']

				# Add query/form parameters to the db
				for p in pair['request']['parameters']:
					paramID = dbm.getParameterID(pathID, method, p['name'])
					dbm.addParameterValue(paramID, p['value'])

				# Add body parameters to the db
				for p, v in pair['request']['body'].items():
					paramID = dbm.getParameterID(pathID, method, p)
					dbm.addParameterValue(paramID, v)

				# Sometimes some responses can be empty. Just avoid to add it to the db
				if pair['response'] != {}:

					# Add response parameters to the db
					isResponseAdded = False
					for p in pair['response']['parameters']:
						if p['name'] == 'Content-Type':
							dbm.addResponse(pathID, method, pair['response']['status'], p['value'], pair['response']['body'])
							isResponseAdded = True
							break
					# Content type is not mandatory, even thought it should be in the message
					# If it is absent, it is assumed ad 'application/octet-stream'
					if not isResponseAdded:
						dbm.addResponse(pathID, method, pair['response']['status'], 'application/octet-stream', pair['response']['body'])

			####     END     ####
				#####################

			pair_number += 1
			pair.clear()


	#####################
	#### POPULATE DB ####
	#dbm.getValues()
	dbm.closeAndCommit()
	####     END     ####
	#####################

	dbfile = confDict['dbPath']
	dbm.create_connection(dbfile)


	res = dbm.getOperationTested()

	operations = []
	for single in res:
		operation = single[1] + " " + single[0]
		operations.append(operation)


	unique_5xx_count = 0
	errors = []
	for stack_trace, count in unique_stack_traces.items():
		error = {"stack_trace": stack_trace, "count": count}
		unique_5xx_count += 1
		errors.append(error)

	dest = confDict['reportsDir']
	# temp fix
	if dest[-1] != '/':
		dest = dest + '/'
	with open(dest + '/generalStats.json', 'w+') as out:
		json.dump({
			"numOperationCovered": len(operations),
			"Operation covered": operations,
			"numErrors": unique_5xx_count,
			"Errors": errors,
			"numberOfInteraction": {
				"total": successfulCount + clientErrorCount + serverErrorCount,
				"2XX": successfulCount,
				"4XX": clientErrorCount,
				"5XX": serverErrorCount
			}
		},
			out,
			indent='\t')
