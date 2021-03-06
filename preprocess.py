# -*- coding: utf-8 -*-
"""
create on Sep 24, 2019

@author: wangshuo
"""

import random
import pickle
import argparse
import numpy as np
import pandas as pd
from tqdm import tqdm
from scipy.io import loadmat
import sys
random.seed(1234)

workdir = 'dataset/'

parser = argparse.ArgumentParser()
parser.add_argument('--dataset', default='Ciao', help='dataset name: Ciao/Epinions')
parser.add_argument('--test_prop', default=0.1, help='the proportion of data used for test')
args = parser.parse_args()

# load data
if args.dataset == 'Ciao':
	click_f = loadmat(workdir + 'Ciao/rating.mat')['rating']
	trust_f = loadmat(workdir + 'Ciao/trustnetwork.mat')['trustnetwork']
elif args.dataset == 'Epinions':
	click_f = np.loadtxt(workdir+'Epinions/ratings_data.txt', dtype = np.int32)
	trust_f = np.loadtxt(workdir+'Epinions/trust_data.txt', dtype = np.int32)
elif args.dataset == "FilmTrust":
	click_f = np.loadtxt(workdir + 'FilmTrust/ratings.txt', dtype = np.int32)
	trust_f = np.loadtxt(workdir+'FilmTrust/trust.txt', dtype = np.int32)	
else:	
	pass 

# print(click_f.shape)
# print(trust_f.shape)
# sys.exit()
click_list = []
trust_list = []

u_items_list = []
u_users_list = []
u_users_items_list = []
i_users_list = []

user_count = 0
item_count = 0
rate_count = 0

for s in click_f:
	# print(s)
	# sys.exit(0)
	uid = s[0]
	iid = s[1]
	if args.dataset == 'Ciao':
		label = s[3]
	elif args.dataset == 'Epinions':
		label = s[2]
	elif args.dataset == "FilmTrust":
		label = s[2]	

	if uid > user_count:
		user_count = uid
	if iid > item_count:
		item_count = iid
	if label > rate_count:
		rate_count = label
	
	click_list.append([uid, iid, label])

# print(user_count, item_count, rate_count)
# sys.exit(0)
pos_list = []
for i in range(len(click_list)):
	pos_list.append((click_list[i][0], click_list[i][1], click_list[i][2]))

# remove duplicate items in pos_list because there are some cases where a user may have different rate scores on the same item.
pos_list = list(set(pos_list))

# train, valid and test data split
random.shuffle(pos_list)
num_test = int(len(pos_list) * args.test_prop)
test_set = pos_list[:num_test]
valid_set = pos_list[num_test:2 * num_test]
train_set = pos_list[2 * num_test:]
print('Train samples: {}, Valid samples: {}, Test samples: {}'.format(len(train_set), len(valid_set), len(test_set)))

with open(workdir + args.dataset + '/dataset.pkl', 'wb') as f:
	pickle.dump(train_set, f, pickle.HIGHEST_PROTOCOL)
	pickle.dump(valid_set, f, pickle.HIGHEST_PROTOCOL)
	pickle.dump(test_set, f, pickle.HIGHEST_PROTOCOL)


train_df = pd.DataFrame(train_set, columns = ['uid', 'iid', 'label'])
valid_df = pd.DataFrame(valid_set, columns = ['uid', 'iid', 'label'])
test_df = pd.DataFrame(test_set, columns = ['uid', 'iid', 'label'])

click_df = pd.DataFrame(click_list, columns = ['uid', 'iid', 'label'])
train_df = train_df.sort_values(axis = 0, ascending = True, by = 'uid')

"""
u_items_list: ????????????????????????????????????iid?????????????????????????????????[(0, 0)]
"""
for u in tqdm(range(user_count + 1)):
	hist = train_df[train_df['uid'] == u]
	u_items = hist['iid'].tolist()
	u_ratings = hist['label'].tolist()
	if u_items == []:
		u_items_list.append([(0, 0)])
	else:
		u_items_list.append([(iid, rating) for iid, rating in zip(u_items, u_ratings)])


with open('user_item.pkl', 'wb') as f:
	pickle.dump(u_items_list, f)
# sys.exit()
# print(u_items_list[1])
# # sys.exit()
train_df = train_df.sort_values(axis = 0, ascending = True, by = 'iid')

"""
i_users_list: ??????????????????????????????????????????????????????????????????[(0, 0)]
"""
for i in tqdm(range(item_count + 1)):
	hist = train_df[train_df['iid'] == i]
	i_users = hist['uid'].tolist()
	i_ratings = hist['label'].tolist()
	if i_users == []:
		i_users_list.append([(0, 0)])
	else:
		i_users_list.append([(uid, rating) for uid, rating in zip(i_users, i_ratings)])
# print(len(i_users_list))
# print(i_users_list[1])
with open('item_user.pkl', 'wb') as f:
	pickle.dump(i_users_list, f)
# sys.exit()
for s in trust_f:
	uid = s[0]
	fid = s[1]
	if uid > user_count or fid > user_count:
		continue
	trust_list.append([uid, fid])

with open('user_user.pkl', 'wb') as f:
	pickle.dump(trust_list, f)
# sys.exit()
trust_df = pd.DataFrame(trust_list, columns = ['uid', 'fid'])
trust_df = trust_df.sort_values(axis = 0, ascending = True, by = 'uid')


"""
u_users_list: ????????????????????????????????????uid???
u_users_items_list: ?????????????????????????????????iid??????
"""
for u in tqdm(range(user_count + 1)):
	hist = trust_df[trust_df['uid'] == u]
	u_users = hist['fid'].unique().tolist()
	if u_users == []:
		u_users_list.append([0])
		u_users_items_list.append([[(0,0)]])
	else:
		u_users_list.append(u_users)
		uu_items = []
		for uid in u_users:
			uu_items.append(u_items_list[uid])
		u_users_items_list.append(uu_items)

if args.dataset == "FilmTrust":
  item_user_list = np.zeros((len(i_users_list), len(u_items_list))) + 1e-8

  for i in range(len(i_users_list)):
    for user, rating in i_users_list[i]:
      item_user_list[i][user] = rating

  average = item_user_list - np.mean(item_user_list, axis=1).reshape(-1,1)
  denom = np.sqrt(np.sum(item_user_list*item_user_list, axis=1))

  sim = average.dot(average.T)

  for i in range(2072):
    for j in range(2072):
      sim[i][j] /= denom[i]*denom[j]

  item_item_list = []

  for i in range(len(sim)):
    array = sim[i][[j for j in range(len(sim[i])) if i != j]]
    item_item_list.append(np.argsort(array)[::-1][:30])

  with open('item_item.pkl', 'wb') as f:
    pickle.dump(item_item_list, f)

  i_items_users_list = []
  for i in tqdm(range(2072)):
    ii_items = []
    for iid in item_item_list[i]:
      ii_items.append(i_users_list[iid])
    i_items_users_list.append(ii_items)

  
  with open('dataset/FilmTrust/i_items_users_list.pkl', 'wb') as f:
    pickle.dump(i_items_users_list, f)
    

print(item_count, len(item_item_list))
with open(workdir + args.dataset + '/list.pkl', 'wb') as f:
  pickle.dump(u_items_list, f, pickle.HIGHEST_PROTOCOL)
  pickle.dump(u_users_list, f, pickle.HIGHEST_PROTOCOL)
  pickle.dump(u_users_items_list, f, pickle.HIGHEST_PROTOCOL)
  pickle.dump(i_users_list, f, pickle.HIGHEST_PROTOCOL)
  pickle.dump(item_item_list, f, pickle.HIGHEST_PROTOCOL)
  pickle.dump(i_items_users_list, f, pickle.HIGHEST_PROTOCOL)
  pickle.dump((user_count, item_count, rate_count), f, pickle.HIGHEST_PROTOCOL)
  


