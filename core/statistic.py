from pathlib import Path
import json

import utils.parsers as parsers
import utils.dbmanager as dbm

dest = None
jsonTestedKey = 'documentedAndTested'
jsonNotTestedKey = 'documentedAndNotTested'
jsonNotExpectedKey = 'notDocumentedAndTested'
jsonFoundKey = 'totalTested'
jsonTotalKey = 'documented'

def getPathCoverage(paths, dbfile):
	dbm.create_connection(dbfile)

	count = dbm.getPathCount()

	testedPaths = dbm.getPathNames()

	untestedPaths = paths.copy()
	for p in testedPaths:
		untestedPaths.remove(p)

	with open(dest + '/path_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : testedPaths, jsonNotTestedKey : untestedPaths}, out, indent='\t')

	dbm.close()

	return {jsonTotalKey : len(paths), jsonTestedKey : count, jsonFoundKey : count}

	with open(dest + 'path_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : testedPaths, jsonNotTestedKey : untestedPaths}, out, indent='\t')

	dbm.close()

	return {jsonTestedKey : count, 'total' : len(paths), jsonNotTestedKey : len(untestedPaths)}


def getOperationCoverage(specDict, dbfile):
	dbm.create_connection(dbfile)

	# Count the number of methods for each path in the specification
	operationsPerPathCount = sum([len(path.keys()) for path in specDict.values()])
	operationsTestedCount = operationsFoundCount = dbm.getOperationCount()
	
	# Get every operation name for every path in the specification
	operationsPerPath = {}
	not_expected = {}
	for path, desc in specDict.items():
		operationsPerPath[path] = list(desc.keys())

	# Get every operation name for every path that has been tested
	operationsTested = dbm.getOperationNames()
	tested = {}
	documentedAndTested = {}
	for r in operationsTested:
		tested.setdefault(r[1], []).append(r[0])

	# Remove tested methods
	# TODO prevedere metodi non nella specifica
	for path in tested:
		# Keep operations in the test set that do not appear in spec
		not_expected[path] = \
			[x for x in tested[path] if x not in operationsPerPath[path]]
		# Keep operations in the spec that do not appear in test set
		operationsPerPath[path] = \
			[x for x in operationsPerPath[path] if x not in tested[path]]
		# Remove the count of the unexpected from the found to get the tested
		operationsTestedCount = operationsTestedCount - len(not_expected[path])
		documentedAndTested[path] = [x for x in tested[path] if x not in not_expected[path]]

	with open(dest + '/operation_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : documentedAndTested, jsonNotTestedKey : operationsPerPath, jsonNotExpectedKey : not_expected}, out, indent='\t')


	dbm.close()

	return {jsonTotalKey : operationsPerPathCount, jsonTestedKey : operationsTestedCount, jsonFoundKey : operationsFoundCount}


def getStatusCoverage(specDict, dbfile):
	dbm.create_connection(dbfile)

	statusInSpecCount = 0
	statusInSpec = {}

	# Get every status possible for each path, operation described in the specification
	for path, vals in specDict.items():
		for method, x in vals.items():
			statusInSpecCount = statusInSpecCount + len(x['responses'])
			
			statusInSpec.setdefault(path, {})
			statusInSpec[path][method] = x['responses']

	# get status tested from the db
	statusTested = dbm.getStatusCodes()
	not_expected = {}
	tested = {}
	statusTestedCount = 0
	
	for path, method, status in statusTested:

		try:
			statusInSpec[path][method].remove(status)
			# Moving those lines before the previous makes the unexpected
			# appear in the tested set
			tested.setdefault(path, {})
			tested[path].setdefault(method, []).append(status)
			statusTestedCount = statusTestedCount + 1

		# There could be more codes than the ones in the specification
		except (KeyError, ValueError):
			not_expected.setdefault(path, {})
			not_expected[path].setdefault(method, []).append(status)
	
	with open(dest + '/status_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : tested, jsonNotTestedKey : statusInSpec, jsonNotExpectedKey : not_expected}, out, indent='\t')

	statusFoundCount = dbm.getStatusCount()

	dbm.close()
	return {jsonTotalKey : statusInSpecCount, jsonTestedKey : statusTestedCount, jsonFoundKey : statusFoundCount}


# TODO
# Update with found. Need to check whether set.add added or not.
def getStatusClassCoverage(specDict, dbfile):
	dbm.create_connection(dbfile)

	statusInSpecCount = 0
	statusInSpec = {}
	for path, vals in specDict.items():
		for method, x in vals.items():
			for code in x['responses']:
				statusInSpec.setdefault(path, {})
				statusInSpec[path].setdefault(method, set()).add(code[0])

			statusInSpecCount = statusInSpecCount + len(statusInSpec[path][method])
		
	not_expected = {}
	tested = {}
	statusTested = dbm.getStatusCodes()

	for path, method, status in statusTested:

		try:
			statusInSpec[path][method].remove(status[0])
			# Moving those lines before the previous makes the unexpected
			# appear in the tested set
			tested.setdefault(path, {})
			tested[path].setdefault(method, set()).add(status[0])

		# There could be more codes than the ones in the specification
		except (KeyError, ValueError):
			not_expected.setdefault(path, {})
			not_expected[path].setdefault(method, set()).add(status[0])

	statusTestedCount = 0

	for path, vals in tested.items():
		for method, x in vals.items():
			statusTestedCount = statusTestedCount + len(x)


		# Cast the sets to dict in order to save it as json
		for path, vals in statusInSpec.items():
			for method, x in vals.items():
				statusInSpec[path][method] = list(x)

		for path, vals in tested.items():
			for method, x in vals.items():
				tested[path][method] = list(x)

		for path, vals in not_expected.items():
			for method, x in vals.items():
				not_expected[path][method] = list(x)

		with open(dest + 'status_class_coverage.json', 'w+') as out:
			json.dump({jsonTestedKey : tested, jsonNotTestedKey : statusInSpec, jsonNotExpectedKey : not_expected}, out, indent='\t')


	dbm.close()
	return {jsonTotalKey : statusInSpecCount, jsonTestedKey : statusTestedCount}


def getResponseContentTypeCoverage(specDict, dbfile):
	dbm.create_connection(dbfile)

	typesInSpecCount = 0
	typesInSpec = {}
	for path, vals in specDict.items():
		for method, x in vals.items():
			typesInSpecCount = typesInSpecCount + len(x['produces'])
			
			typesInSpec.setdefault(path, {})
			typesInSpec[path][method] = x['produces'].copy()

	statusTested = dbm.getResponseTypes()
	not_expected = {}
	tested = {}
	typesTestedCount = 0

	for path, method, t in statusTested:

		try:
			typesInSpec[path][method].remove(t)
			# Moving those lines before the previous makes the unexpected
			# appear in the tested set
			tested.setdefault(path, {})
			tested[path].setdefault(method, []).append(t)
			typesTestedCount = typesTestedCount + 1

		# There could be more codes than the ones in the specification
		except (KeyError, ValueError):
			not_expected.setdefault(path, {})
			not_expected[path].setdefault(method, []).append(t)


	with open(dest + '/response_type_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : tested, jsonNotTestedKey : typesInSpec, jsonNotExpectedKey : not_expected}, out, indent='\t')

	typesFoundCount = dbm.getResponseTypesCount()

	dbm.close()
	return {jsonTotalKey : typesInSpecCount, jsonTestedKey : typesTestedCount, jsonFoundKey : typesFoundCount}


# TODO
# Copia esatta del response. Collassare tutto in una sola funzione?
def getRequestContentTypeCoverage(specDict, dbfile):
	dbm.create_connection(dbfile)

	typesInSpecCount = 0
	typesInSpec = {}
	for path, vals in specDict.items():
		for method, x in vals.items():
			typesInSpecCount = typesInSpecCount + len(x['consumes'])

			typesInSpec.setdefault(path, {})
			typesInSpec[path][method] = x['consumes'].copy()

	statusTested = dbm.getRequestTypes()
	not_expected = {}
	tested = {}
	typesTestedCount = 0

	for path, method, t in statusTested:

		try:
			typesInSpec[path][method].remove(t)
			# Moving those lines before the previous makes the unexpected
			# appear in the tested set
			tested.setdefault(path, {})
			tested[path].setdefault(method, []).append(t)
			typesTestedCount = typesTestedCount + 1

		# There could be more codes than the ones in the specification
		except (KeyError, ValueError):
			not_expected.setdefault(path, {})
			not_expected[path].setdefault(method, []).append(t)

	
	with open(dest + '/request_type_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : tested, jsonNotTestedKey : typesInSpec, jsonNotExpectedKey : not_expected}, out, indent='\t')

	typesFoundCount = dbm.getRequestTypesCount()

	dbm.close()
	return {jsonTotalKey : typesInSpecCount, jsonTestedKey : typesTestedCount, jsonFoundKey : typesFoundCount}


def getParameterCoverage(specDict, dbfile):
	dbm.create_connection(dbfile)

	parametersInSpecCount = 0
	parametersInSpec = {}
	for path, vals in specDict.items():
		for method, x in vals.items():
			parametersInSpecCount = parametersInSpecCount + len(x['parameters'])
			
			parametersInSpec.setdefault(path, {})
			parametersInSpec[path][method] = list(x['parameters'].keys())

	parametersTested = dbm.getParameters()
	not_expected = {}
	tested = {}
	parametersTestedCount = 0

	for path, method, param in parametersTested:

		try:
			parametersInSpec[path][method].remove(param)
			# Moving those lines before the previous makes the unexpected
			# appear in the tested set
			tested.setdefault(path, {})
			tested[path].setdefault(method, []).append(param)
			parametersTestedCount = parametersTestedCount + 1

		# There could be more codes than the ones in the specification
		except (KeyError, ValueError):
			not_expected.setdefault(path, {})
			not_expected[path].setdefault(method, []).append(param)
	
	with open(dest + '/parameter_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : tested, jsonNotTestedKey : parametersInSpec, jsonNotExpectedKey : not_expected}, out, indent='\t')

	parametersFoundCount = dbm.getParametersCount()

	dbm.close()
	return {jsonTotalKey : parametersInSpecCount, jsonTestedKey : parametersTestedCount, jsonFoundKey : parametersFoundCount}


def getParameterValueCoverage(specDict, dbfile):
	dbm.create_connection(dbfile)

	# Extract compatible parameters from specification
	pvalCompatibleCount = 0
	pvalCompatible = {}

	pvalTestedCount = 0
	tested = {}
	not_expected = {}

	for path, vals in specDict.items():
		path_id = dbm.getPathIDByName(path)

		if path_id is None:
			continue
		for method, x in vals.items():
			for p, v in x['parameters'].items():
				if len(v) > 0:

					v = set(v)
					testedValues = dbm.getParameterValues(path_id, method, p)
					testedValues = set(testedValues) if testedValues is not None else set()

					tested.setdefault(path, {})
					tested[path].setdefault(method, {})
					tested[path][method][p] = list(v.intersection(testedValues))

					pvalTestedCount = pvalTestedCount + len(tested[path][method][p])
					pvalCompatibleCount = pvalCompatibleCount + len(v)

					not_expected.setdefault(path, {})
					not_expected[path].setdefault(method, {})
					not_expected[path][method][p] = list(testedValues - v)

					pvalCompatible.setdefault(path, {})
					pvalCompatible[path].setdefault(method, {})
					pvalCompatible[path][method][p] = list(v - testedValues)

	with open(dest + '/parameter_value_coverage.json', 'w+') as out:
		json.dump({jsonTestedKey : tested, jsonNotTestedKey : pvalCompatible, jsonNotExpectedKey : not_expected}, out, indent='\t')

	return {jsonTotalKey : pvalCompatibleCount, jsonTestedKey : pvalTestedCount}

def computeTCL(coverageDictionary):
	# TCL 0
	tcl = 0

	# TCL 1
	if coverageDictionary['pathCoverage']['rate'] >= 1:
		tcl += 1
	else:
		return tcl

	# TCL 2
	if coverageDictionary['operationCoverage']['rate'] >= 1:
		tcl += 1
	else:
		return tcl

	# TCL 3
	if coverageDictionary['responseTypeCoverage']['rate'] >= 1 and coverageDictionary['requestTypeCoverage']['rate'] >= 1:
		tcl += 1
	else:
		return tcl

	# TCL 4
	if coverageDictionary['statusClassCoverage']['rate'] >= 1 and coverageDictionary['parameterCoverage']['rate'] >= 1:
		tcl += 1
	else:
		return tcl

	# TCL 5
	if coverageDictionary['statusCoverage']['rate'] >= 1:
		tcl += 1
	else:
		return tcl

	# TCL 6
	if coverageDictionary['parameterValueCoverage']['rate'] >= 1:
		tcl += 1
	else:
		return tcl



def generateStats(specDict, confDict):
	global dest

	calcRate = lambda d : d[jsonTestedKey] / d[jsonTotalKey] if d[jsonTotalKey] != 0 else None
	newStatEntry = lambda d : {'raw' : d, 'rate' : calcRate(d)}

	dest = confDict['reportsDir']
	#temp fix
	if dest[-1] != '/':
		dest = dest + '/'
	dbfile = confDict['dbPath']
	covDict = {}
	paths = list(specDict.keys())

	#-----------
	pathCovergage = getPathCoverage(paths, dbfile)
	covDict['pathCoverage'] = newStatEntry(pathCovergage)

	#-----------
	operationCoverage = getOperationCoverage(specDict, dbfile)
	covDict['operationCoverage'] = newStatEntry(operationCoverage)

	#-----------
	statusClassCoverage = getStatusClassCoverage(specDict, dbfile)
	covDict['statusClassCoverage'] = newStatEntry(statusClassCoverage)

	#-----------
	statusCoverage = getStatusCoverage(specDict, dbfile)
	covDict['statusCoverage'] = newStatEntry(statusCoverage)

	#-----------
	respTypeCoverage = getResponseContentTypeCoverage(specDict, dbfile)
	covDict['responseTypeCoverage'] = newStatEntry(respTypeCoverage)

	#-----------
	reqTypeCoverage = getRequestContentTypeCoverage(specDict, dbfile)
	covDict['requestTypeCoverage'] = newStatEntry(reqTypeCoverage)

	#-----------
	paramCoverage = getParameterCoverage(specDict, dbfile)
	covDict['parameterCoverage'] = newStatEntry(paramCoverage)

	#-----------
	paramValueCoverage = getParameterValueCoverage(specDict, dbfile)
	covDict['parameterValueCoverage'] = newStatEntry(paramValueCoverage)

	covDict['TCL'] = computeTCL(covDict)

	with open(dest + '/stats.json', 'w+') as out:
		json.dump(covDict, out, indent='\t')
		print('Metrics and statistics computed successfully. Reports are available at', dest)




	