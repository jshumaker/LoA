import itertools
import yaml
import sys
import argparse

with open('tt.yml', 'r') as f:
    config = yaml.safe_load(f)

if not 'players' in config or not 'teams' in config:
    print('ERROR: Missing players or teams in tt.yml')
    sys.exit(1)

players = config['players']
teams = config['teams']


def simulate_player_battle(player1, player2):
    if player1 in players and player2 in players[player1]:
        return players[player1][player2]
    if player2 in players and player1 in players[player2]:
        return not players[player2][player1]
    print("ERROR: No matchup found for {0} vs {1}, please update config".format(player1, player2))
    sys.exit(1)


def simulate(team1, team2):
    fight_count = 0
    winner = 0
    team1_pos = 0
    team2_pos = 0
    while team2_pos < 5 and team1_pos < 5:
        if simulate_player_battle(team1[team1_pos], team2[team2_pos]):
            #print('{0} beats {1}'.format(team1[team1_pos], team2[team2_pos]))
            team2_pos += 1
            if winner != 1:
                winner = 1
                fight_count = 1
            else:
                fight_count += 1
        else:
            #print('{0} beats {1}'.format(team2[team2_pos], team1[team1_pos]))
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

def find_winning_orders(team1, team2):
    """
    :param team1: The team you want to find wins for.
    :param team2: The team you want to lose, in the order you're checking.
    :return: List of orders for team1 which beat team2.
    """
    winning_orders = []
    for team1order in list(itertools.permutations(team1, 5)):
        if simulate(team1order, team2):
            winning_orders.append(team1order)
    return winning_orders


parser = argparse.ArgumentParser(description='Automatically play LoA Gemology')
parser.add_argument('team1', help="First team in comparison, the team you want to win.")
parser.add_argument('team2', help="Second team in comparison, the team you want to lose.")
parser.add_argument('--counter', action='store_true', help="Display counter orders by team1 that beat team2")
args = parser.parse_args()

if not args.team1 in teams:
    print("ERROR: team not found: {0}".format(args.team1))
    sys.exit(1)
if not args.team2 in teams:
    print("ERROR: team not found: {0}".format(args.team2))
    sys.exit(1)

print("Team 1 current order: " + ', '.join(teams[args.team1]))
print("Team 2 current order: " + ', '.join(teams[args.team2]))

# First assume the team2 is following the current order, find formations that beat it.
print("="*80)
print("Formations which beat {0}:".format(', '.join(teams[args.team2])))
for order in find_winning_orders(teams[args.team1], teams[args.team2]):
    print(', '.join(order))

# Find the best formations against sane formations (ones that have some chance of winning) by the other team.
print("="*80)
print('Formations chances against sane formations by the opposing team.')

team2_results = get_results(teams[args.team2], teams[args.team1])
sane_team2_orders = [result[0] for result in team2_results if result[1] > 0.0]
if len(sane_team2_orders) == 0:
    print("The other team has no chance to beat you!")
else:
    results = compare_formationlists(list(itertools.permutations(teams[args.team1], 5)), sane_team2_orders)
    for order, chance in results:
        if chance > 0.0:
            print('{0}% chance of winning Order: {1}'.format(chance, ', '.join(order)))


# Figure out team2 counter orders to team1's current order, then figure out team1's best counters to those counters.
print("="*80)
print('Calculating best counter counter orders:')
counters = []
for order in list(itertools.permutations(teams[args.team2], 5)):
    if not simulate(teams['moo'], order):
        print('Loses to: ' + ', '.join(order))
        counters.append(order)

if len(counters) == 0:
    print("Opposing team has no viable counters.")
    sys.exit(0)

counter_counters = compare_formationlists(list(itertools.permutations(teams[args.team1], 5)), counters)
for order, chance in counter_counters:
    if chance > 0.0:
        if simulate(order,teams[args.team2]):
            print('{0}% chance of winning, beats old order Order: {1}'.format(chance, ', '.join(order)))
        else:
            print('{0}% chance of winning, lose to old order Order: {1}'.format(chance, ', '.join(order)))