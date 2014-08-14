#!/bin/python
import itertools


class Player:
	def __init__(self, name, power):
		self.Name = name
		self.Power = power

team_moo = [
	Player('Shep', 10),
	Player('Xyern', 9),
	Player('Tiver', 6),
	Player('Kirya', 5),
	Player('NemesiS', 4)
]

team_lycan = [
	Player('Lycan', 15),
	Player('kappy', 8),
	Player('azzy', 3),
	Player('robjohnson', 3),
	Player('chucky80', 3)
]


def simulate(team1, team2):
	fight_count = 0
	winner = 0
	team1_pos = 0
	team2_pos = 0
	while team2_pos < 5 and team1_pos < 5:
		if team1[team1_pos].Power > team2[team2_pos].Power:
			#print('{0} beats {1}'.format(team1[team1_pos].Name, team2[team2_pos].Name))
			team2_pos += 1
			if winner != 1:
				winner = 1
				fight_count = 1
			else:
				fight_count += 1
		else:
			#print('{0} beats {1}'.format(team2[team2_pos].Name, team1[team1_pos].Name))
			team1_pos += 1
			if winner != 2:
				winner = 2
				fight_count = 1
			else:
				fight_count += 1
		# After 3 wins, someone gets booted, unless the battle is already over.
		if fight_count == 3 and team1_pos < 5 and team2_pos < 5:
			if winner == 1:
				#print('{0} Must retire.'.format(team1[team1_pos].Name))
				team1_pos += 1
			else:
				#print('{0} Must retire.'.format(team2[team2_pos].Name))
				team2_pos += 1
			winner = 0
			fight_count = 0
	return team1_pos < team2_pos

def get_order(team):
	players = team[0].Name
	for player in team[1:]:
		players += ', ' + player.Name
	return players
	

def compare_formationlists(formations1, formations2):
	results = []
	for order1 in formations1:
		wins = 0
		losses = 0
		#print('Checking  order: {0}'.format(get_order(order1)))
		for order2 in formations2:
			if simulate(order1, order2):
				wins += 1
			else:
				losses += 1
		#print('Wins: {0}'.format(wins))
		results.append([order1, wins * 100.0 / (wins + losses)])
		
	return sorted(results, reverse=True, key=lambda result: result[1])

def get_results(team1, team2):
	"""
	Checks all permutations
	"""
	#print('Team: {0}'.format(get_order(team1)))
	#print('Versus: {0}'.format(get_order(team2)))
	return compare_formationlists(list(itertools.permutations(team1, 5)), list(itertools.permutations(team2, 5)))

#lycan_results = get_results(team_lycan, team_moo)
#sane_orders = [result[0] for result in lycan_results if result[1] >= 50.0]

#results = compare_formationlists(list(itertools.permutations(team_moo, 5)), sane_orders)
#results = get_results(team_moo,team_lycan)	
#for result in results:
#	print('{0}% chance of winning Order: {1}'.format(result[1], get_order(result[0])))

	
# Test a formations
team_moo = [
	Player('Tiver', 6),
	Player('Xyern', 9),
	Player('Kirya', 5),
	Player('NemesiS', 4),
	Player('Shep', 10),
]
print('test formation: ' + get_order(team_moo))
counters = []
for order in list(itertools.permutations(team_lycan, 5)):
	if not simulate(team_moo, order):
		print('Loses to: ' + get_order(order))
		counters.append(order)

counter_counters = compare_formationlists(list(itertools.permutations(team_moo, 5)), counters)
print('Best Counter Counters:')
for result in counter_counters:
	print('{0}% chance of winning Order: {1}'.format(result[1], get_order(result[0])))