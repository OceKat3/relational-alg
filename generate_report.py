from parser import Relation
from test import parse_to_ast

from random import randint

def generate_two_relations(n:int,match_rate:float=2) :

    natural_numbers = Relation(
        cols=['b', 'c'],
        data=[
            [int(x/match_rate), x] for x in range(n)
        ]
    )

    random_joiners = Relation(
        cols = ['a', 'b'],
        data = [
            [x, randint(0, int(n/match_rate))] 
            for x in range(n)
        ] #type: ignore
    )
    
    return {"R":random_joiners, "S":natural_numbers}

from time import time

def q1():

    print('1. does the size of relations affect the complexity of join?\n')

    document = "R join[R.b=S.b] S"

    for i in range(7) :
        n = 20 * (2 ** i)

        print(n, end='   ')

        known = generate_two_relations(n)

        ast = parse_to_ast(document)

        result = ast.eval([], known)        

        print(ast.counter, 'comparisons', end='   ')
        print(len(result.data), 'output tuples', end='   ')

        iters=1
        start = time()
        for i in range(iters):
            ast.eval([], known)
        end = time()
        time_per_iter = (end - start) / iters

        print('wall: ', time_per_iter, end='   ')
        print()

def q3():

    print('3. does the size of relations affect the complexity of operations like select/project?\n')

    document = "select[b>20](R)"

    for i in range(7) :
        n = 1000 * (2 ** i)

        print(n, end='   ')

        known = generate_two_relations(n)

        ast = parse_to_ast(document)

        result = ast.eval([], known)        

        print(ast.predicate.counter, 'comparisons', end='   ')
        print(len(result.data), 'output tuples', end='   ')

        iters=8
        start = time()
        for i in range(iters):
            ast.eval([], known)
        end = time()
        time_per_iter = (end - start) / iters

        print('wall: ', time_per_iter, end='   ')
        print()

# q1()

# q3()

def q5():

    print('5. does the match rate affects the number of comparisons a join makes? wall time?\n')

    document = "R join[R.b=S.b] S"

    for i in range(-3, 8) :
        n = 200
        match_rate = 1.8 ** i
        
        print('match rate', match_rate, end='     ')

        known = generate_two_relations(n, match_rate)

        ast = parse_to_ast(document)

        result = ast.eval([], known)        

        print(ast.counter, 'comparisons', end='   ')
        print(len(result.data), 'output tuples', end='   ')

        iters=4
        start = time()
        for i in range(iters):
            ast.eval([], known)
        end = time()
        time_per_iter = (end - start) / iters

        print('wall: ', time_per_iter, end='   ')
        print()

q5()