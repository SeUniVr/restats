from pathlib import Path
import re
import json

import utils.parsers as parsers
import utils.dbmanager as dbm

def generatePairs(confDict, pathsInSpec, basesInSpec):
	source = confDict['dumpsDir']
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
	prev_number = '' # previous file number
	pair = {} # pair map for easy json writing

	#####################
	#### POPULATE DB ####
	dbm.create_connection(dbFile)
	dbm.createTables()
	####     END     ####
	#####################


	# Gets every entry in the directory, and keeps only files
	files_in_source = (entry for entry in Path(source).iterdir() if entry.is_file())
	files_in_source = sorted(files_in_source)

	for file in files_in_source:

		#print('pair number: ', prev_number)

		if prev_number == '':
			prev_number = file.name.split('-')[0]
			request = parsers.RawHTTPRequest2Dict(file)
			pair['pairNumber'] = prev_number

			# To check if a path matches one in the spec
			match = False
			#print('actual path: ', request['path'])

			# replace the path extracted from the request with the specification matching one
			for (r, path) in zip(paths_re, pathsInSpec):
				#print('re:', r, 'path:', path)

				if (r.match(request['path'])):
					match = True
					request['path'] = path
					break

			#x = input()
			pair['request'] = request

		elif prev_number == file.name.split('-')[0]:
			response = parsers.RawHTTPResponse2Dict(file)
			pair['response'] = response

			#parsers.pair2json(pair, prev_number, dest)

			# If there is no match with the API specification paths
			# The path is ignored and not counted in the statistics.
			if not match:
				unmatched.append(pair['request']['path'])
				prev_number = ''
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
						dbm.addResponse(pathID, method, pair['response']['status'], p['value'])
						isResponseAdded = True
						break
				# Content type is not mandatory, even thought it should be in the message
				# If it is absent, it is assumed ad 'application/octet-stream'
				if not isResponseAdded:
					dbm.addResponse(pathID, method, pair['response']['status'], 'application/octet-stream')

			####     END     ####
			#####################

			prev_number = ''
			pair.clear()

		else:
			unmatched.append(file.name)

	#####################
	#### POPULATE DB ####
	#dbm.getValues()
	dbm.closeAndCommit()
	####     END     ####
	#####################