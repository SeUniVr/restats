from urllib.parse import parse_qs, urlsplit
import json
import tempfile

methodsWithRequestBody = {'post', 'put', 'patch'}

def RawHTTPRequest2Dict(requestFile):
	"""
	Parses a raw HTTP Request from a file and casts it to a dictionary.
	"""

	method = ''
	url = ''
	endpoint = ''
	parameters = []
	body = {}
	hasFormParams = hasJSONbody = False

	tmp = tempfile.NamedTemporaryFile()

	# Open the file for writing.
	with open(tmp.name, 'w') as f:
		f.write(requestFile)  # where `stuff` is, y'know... stuff to write (a string)

	with open(tmp.name, 'rb') as f:
		line = str(f.readline(), 'UTF-8')
		line = line.split()

		method = line[0]
		url = line[1]
		version = line[2]
		path = urlsplit(url)[2]

		# Parse query parameters
		# It is a dictionary like
		# {param_name : [param_value]}
		queryParam = parse_qs(urlsplit(url)[3])

		# Add query parameters in the parameters dictionary
		for k, v in queryParam.items():
			parameters.append({'in' : 'query', 'name' : k, 'value' : v[0]})

		# The first line has already been read. The next lines contain the headers
		lines = f.readlines()
		for i in range(len(lines)):
			line = str(lines[i], 'UTF-8')

			# If an empty line is found, then there are no other headers.
			# There could only be some POST parameters left to parse.
			if line == '\n' :
				stop = i
				break

			line = line.split(':')
			name = line[0]
			value = ':'.join([x.strip(' \r\n') for x in line[1:]])

			# Remove burp plugin injected header
			if name == 'X-Burp-Comment': continue

			# Add every header as parameter
			parameters.append({ 'in' : 'header', 'name' : name, 'value' : value})

			# Check if POST (form) parameters are present
			if name == 'Content-Type' and value == 'application/x-www-form-urlencoded':
				hasFormParams = True

			# Check if there is a json body
			elif name == 'Content-Type' and value in ('application/vnd.api+json', 'application/json'):
				hasJSONbody = True

		if  hasFormParams:

			line = str(f.readline(), 'UTF-8')
			formParams = parse_qs(line)

			for k, v in formParams.items():
				parameters.append({'in' : 'query', 'name' : k, 'value' : v[0]})

		elif hasJSONbody:
			lines = [str(x, 'UTF-8') for x in lines[stop + 1:]]
			lines = " ".join(lines)

			try:
				body = dict(json.loads(lines))
			except:
				body = {}

	return {
	'method' : method.lower(),
	'url' : url,
	'version' : version,
	'path' : path,
	'parameters' : parameters,
	'body' : body
	}

def RawHTTPResponse2Dict(responseFile):
	"""
	Parses a raw HTTP Response from a file and casts it to a dictionary.
	"""

	status = ''
	message = ''
	parameters = []
	body = ''

	tmp = tempfile.NamedTemporaryFile()

	# Open the file for writing.
	with open(tmp.name, 'w') as f:
		f.write(responseFile)  # where `stuff` is, y'know... stuff to write (a string)

	# Have to open the file as binary because of the payload
	with open(tmp.name, 'rb') as f:
		line = str(f.readline(), 'UTF-8')

		# Check whether the file is empty or not
		if line == '' : return {}

		line = line.split()

		status = line[1]
		message = ' '.join(line[2:]) #Joins with a whitespace all the words from the message

		stop = None
		# The first line has already been read. The next lines contain the headers
		lines = f.readlines()
		for i in range(len(lines)):
			line = str(lines[i], 'UTF-8')
			# If an empty line is found, then there are no other headers.
			if line == '\n':
				stop = i
				break

			line = line.split(':')

			# Remove burp plugin injected header
			if line[0] == 'X-Burp-Comment': continue

			# If the header is the content type, cut out the charset part (if any)
			if line[0] == 'Content-Type':
				line[1] = line[1].split(';')[0]

			parameters.append({ 'in' : 'header', 'name' : line[0], 'value' : ':'.join([x.strip(' \r\n') for x in line[1:]])})
		if stop is not None:
			# parse body
			lines = [str(x, 'UTF-8') for x in lines[stop + 1:]]
			lines = "".join(lines)
			body += lines
	return {
	'status' : status,
	'message' : message,
	'parameters' : parameters,
	'body' : body
	}


def pair2json(pairDict, number, dirPath):
	"""
	Takes a dictionary with a pair request/response and saves it as a JSON file.
	The suffix of the file name depends on the current pair number retrieved from
	the log files.
	"""
	filename = dirPath + number + '-' + '/pair.json'

	with open(filename, 'w+') as out:
		json.dump(pairDict, out, indent='\t')


def json2pair(jsonFile):

	with open(jsonFile) as jf:
		data = json.load(jf)

		return data


def extractSpecificationData(specFile):
	'''
	In pratica questo parsing servirà solamente a rimuovere dei campi alla specifica
	e renderla più fruibile come python dict e non come un json (scomodo per ottenere
	la maggior parte dei risultati). 
	{
	'path1' :
		{
		'GET' : 
		{
			'parameters' : 
			{
				'param1' : {enum1, enum2},
				'param2' : {true, false},
				'param3' : {}
			},
			'responses' : {status1, status2, status3, ...},
			'produces' : {type1, type2, type3, ...},
			'consumes' : {type1, type2, type3, ...}
		},
		'POST': 
		{
			'parameters' : 
			{
				'param1' : {enum1, enum2},
				'param2' : {true, false},
				'param3' : {}
			},
			'responses' : {status1, status2, status3, ...},
			'produces' : {type1, type2, type3, ...},
			'consumes' : {type1, type2, type3, ...}
		}
	}

	Per i parametri bisogna anche salvare la posizione per evitare la sovrapposizione di 
	parametri con lo stesso nome in luoghi differenti. In caso il parametro sia un enum 
	o un bool, vengono salvati i possibili valori. 
	Il tutto va in un dizionario di dizionario di set (più comodi rispetto ad una lista).
	Gli status e i content-type possono andare in un semplice set.
	'''

	try:
		with open(specFile) as spec:
			data = json.load(spec)

		# Check the specification version
		if 'swagger' in data.keys():
			extractedData =  parseSwagger2(data)

		elif 'openapi' in data.keys():
			extractedData =  parseOpenAPI3(data)

		else:
			raise Exception('Version not parsable')

		return extractedData

	except:
		print('Could not open specification file.')
		quit()

def parseOpenAPI3(data):
	newSpec = dict()

	# Add the base path of every resource served by the API
	if 'servers' in data.keys():
		newSpec['bases'] = [urlsplit(s['url'])[2] for s in data['servers']]
		# Since the standard defines that every path MUST begin with a '/', it is
		# not needed in the base path
		newSpec['bases'] = [p[0:-1] if len(p) > 0 and p[-1] == '/' else p for p in newSpec['bases']]
		newSpec['bases'] = list(set(newSpec['bases']))
	else:
		newSpec['bases'] = ['/']


	# Iterate through all the paths in the specification
	for path in data['paths']:
		newSpec[path] = {}

		# Iterate through all the methods of a path
		for method in data['paths'][path]:
			method = method.lower()
			
			newSpec[path][method] = \
				{'parameters' : {}, 'pathParameters': [], 'responses' : [], 'produces' : [], 'consumes' : []}

			# Get every parameter description for the method
			# Before check it there are parameters
			if 'parameters' in data['paths'][path][method].keys():

				for parameter in data['paths'][path][method]['parameters']:

					# If parameter in path treat it differently (for parameter coverage)
					if parameter['in'] == 'path':
						newSpec[path][method]['pathParameters'].append(parameter['name'])

					# In OpenAPI 3 there could be schema xor content
					elif 'schema' in parameter.keys():

						if 'enum' in parameter['schema'].keys():
							newSpec[path][method]['parameters'][parameter['name']] = parameter['schema']['enum']

						elif parameter['schema']['type'] == 'boolean':
							# Use true, false instead of False, True because of python json serialization
							newSpec[path][method]['parameters'][parameter['name']] = ['true', 'false']

						else:
							newSpec[path][method]['parameters'][parameter['name']] = []

					else:
						newSpec[path][method]['parameters'][parameter['name']] = []


			# Extract status codes
			for status, val in data['paths'][path][method]['responses'].items():
				newSpec[path][method]['responses'].append(status)

				# Extract output content-types
				if 'content' in val.keys():
					newSpec[path][method]['produces'] = newSpec[path][method]['produces'] + list(val['content'].keys())

			# Extract input content-types
			if method in methodsWithRequestBody:

				# Check the content-type header parameter
				# It overwrites the consumes: this header is always present in an HTTP request.
				if 'Content-Type' in newSpec[path][method]['parameters'].keys():
					newSpec[path][method]['consumes'] = newSpec[path][method]['parameters']['Content-Type']

				elif 'requestBody' in data['paths'][path][method].keys():
					newSpec[path][method]['consumes'] = list(data['paths'][path][method]['requestBody']['content'].keys())

			# Remove duplicates in produces and consumes
			newSpec[path][method]['produces'] = list(set(newSpec[path][method]['produces']))
			#newSpec[path][method]['consumes'] = list(set(newSpec[path][method]['consumes']))

	return newSpec


def parseSwagger2(data):
	newSpec = dict()

	defaultConsumes = [] # only affects operations with a request body
	defaultProduces = []

	# Set default consumes & produces
	if 'consumes' in data.keys():
		defaultConsumes = data['consumes']
	if 'produces' in data.keys():
		defaultProduces = data['produces']

	# Add the base path of every resource served by the API
	if 'basePath' in data.keys():
		p = data['basePath']
		# Since the standard defines that every path MUST begin with a '/', it is
		# not needed in the base path
		newSpec['bases'] = [p[0:-1] if len(p) > 0 and p[-1] == '/' else p]
	else:
		newSpec['bases'] = ['']

	# Iterate through all the paths in the specification
	for path in data['paths']:
		newSpec[path] = {}

		# Iterate through all the methods of a path
		for method in data['paths'][path]:
			method = method.lower()

			newSpec[path][method] = \
				{'parameters' : {}, 'pathParameters' : [], 'responses' : [], 'produces' : [], 'consumes' : []}

			# Get every parameter description for the method
			# Before check if there are parameters
			if 'parameters' in data['paths'][path][method].keys():

				for parameter in data['paths'][path][method]['parameters']:

					# If parameter in path treat it differently (for parameter coverage)
					if parameter['in'] == 'path':
						newSpec[path][method]['pathParameters'].append(parameter['name'])

					# If parameter in body it is not counted in the parameter coverage, so it is not added
					elif parameter['in'] == 'body':
						continue

					# If the parameter has the 'enum' field, save the possible values
					elif 'enum' in parameter.keys():
						newSpec[path][method]['parameters'][parameter['name']] = parameter['enum']

					# schema is only used with in: body parameters. Any other parameters expect a primitive type
					# there cuold be schema instead of type
					elif 'type' in parameter.keys() and parameter['type'] == 'boolean':
						# Use true, false instead of False, True because of python json serialization
						newSpec[path][method]['parameters'][parameter['name']] = ['true', 'false']

					else:
						newSpec[path][method]['parameters'][parameter['name']] = []

			# Extract status codes
			newSpec[path][method]['responses'] = list(data['paths'][path][method]['responses'].keys())

			# Extract input content-types
			if method in methodsWithRequestBody:

				# Check the content-type header parameter
				# It overwrites the consumes: this header is always present in an HTTP request.
				if 'Content-Type' in newSpec[path][method]['parameters'].keys():
					newSpec[path][method]['consumes'] = newSpec[path][method]['parameters']['Content-Type']

				elif 'consumes' in data['paths'][path][method].keys():
					newSpec[path][method]['consumes'] = data['paths'][path][method]['consumes']

				else:
					newSpec[path][method]['consumes'] = defaultConsumes

				# Check also the content-type header parameter

			# Extract output content-types
			if 'produces' in data['paths'][path][method].keys():
				newSpec[path][method]['produces'] = data['paths'][path][method]['produces']
			else:
				newSpec[path][method]['produces'] = defaultProduces

	return newSpec

				


if __name__ == '__main__':

	d = extractSpecificationData('../specifications/slim.json')

	print(d)
	