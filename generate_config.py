#!/usr/bin/env python3

import math
import queue
import multiprocessing
import sys
import glob, os

max_workers_num = multiprocessing.cpu_count()

ips_range = [
	'1.1.1.1-1.1.1.9',
]

print('This script generates configuration for squid workers.')

# получаем кол. воркеров
while True:
	workers_num = input("Enter Squid workers num (default your system %s): " % max_workers_num)

	if workers_num is '':
		workers_num = max_workers_num

	try:
		workers_num = int(workers_num)

		if workers_num > max_workers_num:
			print('ERROR: enter a value less than %s' % max_workers_num)
			continue

		break
	except:
		print('ERROR: invalid value')


# получаем диапазоны IP:
while True:
	ips_range_str = input("Enter the IP address or range of addresses comma separated (example: 1.1.1.2-1.1.1.5,2.2.2.2): ")

	if ips_range_str is '':
		print('ERROR: invalid value')
		continue
	else:
		final_ips = queue.Queue()

		for ip_range in ips_range_str.split(','):
			if '-' not in ip_range:
				print('ip_range', ip_range)
				final_ips.put(ip_range)
				continue

			ip_start, ip_end = ip_range.split('-')

			ip_base = '%s.' % '.'.join(ip_start.split('.')[:-1])
			start = int(ip_start.split('.')[-1])
			end = int(ip_end.split('.')[-1])

			if end <= start:
				print('END: ', end, '<', 'START:', start)

			for ip in range(start, end + 1):
				final_ips.put('%s%s' % (ip_base, ip))

		if final_ips.qsize() == 0:
			print('ERROR: invalid value')
			continue

		break

print('\n\nRecently confirmation!')
print('Configuration files are generated for %s workers.' % workers_num)
print('IPs num: %s' % final_ips.qsize())
print('All files on this template will be removed: include_workers.conf, worker-*.conf\n\n')

confirmation = input("All right? [y/n]: ")

if 'y' not in confirmation and 'д' not in confirmation:
	sys.exit()

print('\n\n\n')

# удаляем старые конфиги
os.chdir("./")
for file in glob.glob("worker-*.conf"):
	os.remove(file)
	print('REMOVE:', file)

try:
	os.remove('include_workers.conf')
	print('REMOVE:', 'include_workers.conf')
except:
	pass
try:
	os.remove('mongo_update.js')
	print('REMOVE:', 'mongo_update.js')
except:
	pass

i = 0
worker_i = 1
configs = {}
all_ips = []
all_ips_insert = []
while True:
	i += 1

	if final_ips.qsize() == 0:
		break

	if worker_i > workers_num:
		worker_i = 1
		continue

	if worker_i not in configs:
		configs[worker_i] = ''

	ip = final_ips.get()

	name = 'ssip%s' % i

	configs[worker_i] += 'acl %s myip %s\n' % (name, ip)
	configs[worker_i] += 'tcp_outgoing_address %s %s\n' % (ip, name)

	worker_i += 1

	all_ips.append(ip)
	all_ips_insert.append("{type: 'proxy', enabled: true, protocol: 'http', port: '901', proxy: '%s', groups: ['se_google', 'se_yandex']}" % ip)

print('\n\n')

main_config = ''
for worker_i in configs:
	file_name = 'worker-%s.conf' % worker_i

	print('GENERATE:', file_name)

	f = open(file_name, 'w')
	f.write(configs[worker_i])
	f.close()

	main_config += 'if ${process_number} = %s\n' % worker_i
	main_config += 'include /etc/squid/%s\n' % file_name
	main_config += 'endif\n'

main_config = 'workers %s\n\n%s' % (workers_num, main_config)
main_file_name = 'include_workers.conf'

f = open(main_file_name, 'w')
f.write(configs[worker_i])
f.close()

print('GENERATE:', main_file_name)


mongo_file_name = 'mongo_update.js'
print('GENERATE:', mongo_file_name)
f = open(mongo_file_name, 'w')
f.write("db.trees.remove({type: 'proxy', proxy: {'$in': ['%s']}});\n" % "','".join(all_ips))
f.write("db.trees.insert([%s]);\n" % ','.join(all_ips_insert))
f.close()


print('\n\n')
print('------------------')
print('1. Add to /etc/squid/squid.conf:')
print('include include_workers.conf')
print(' ')
print('2. Move all *.conf files to /etc/squid/')
print('mv  *.conf /etc/squid/')
print(' ')
print('3. Run the query to update the mongodb:')
print('mongo  <SERVER ADDRESS>/<DATABASE NAME> < mongo_update.js')
print(' ')
print('4. Restart squid:')
print('service squid restart')
print(' ')
print('5. Restart proxy queue script')
print('\n\n')