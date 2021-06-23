from pathlib import Path
import sys
import json

import core.pairing as pairing
import core.statistic as stat
import utils.parsers as par

def callOptionMethod(confDict):

	modules = confDict['modules']

	# Extract data from specification (needed to parse pairs)
	specDict = par.extractSpecificationData(conf['specification'])
	# Pop the base paths of the API
	bases = specDict.pop('bases')

	if modules == 'dataCollection':
		paths = list(specDict.keys())
		pairing.generatePairs(confDict, paths, bases)

	elif modules == 'statistics':
		stat.generateStats(specDict, confDict)

	elif modules == 'all':
		paths = list(specDict.keys())
		pairing.generatePairs(confDict, paths, bases)
		stat.generateStats(specDict, confDict)

	else:
		raise Exception('Wrong module. [pair/statistics/all]')


if __name__ == '__main__':

	try:
		cFilePath = sys.argv[1]
	except:
		cFilePath = "config.json"

	# Read configuration file
	with open(cFilePath) as j:
		conf = json.load(j)

	for k in conf:
		conf[k] = conf[k][:-1] if conf[k][-1] == '/' else conf[k]

	callOptionMethod(conf)

'''	verbose = conf['verbose']

	# Extract data from specification (needed to parse pairs)
	specDict = par.extractSpecificationData(conf['specification'])
	# Pop the base paths of the API
	bases = specDict.pop('bases')
	paths = list(specDict.keys())

	if conf['option'] == 'pair':	
		pairing.generatePairs(conf, paths, bases)

	elif conf['option'] == 'statistics':
		stat.generateStats(specDict, conf['reportDirPath'], conf['dbFilePath'])

	else:
		raise Exception('Not implemented. WIP.')'''