from example_relations import example_relations
from parser import tokenizer, Recognizer, Parser, RelationalTreeReducer, Relation

from typing import Literal

from pprint import pprint

mode:Literal['parsetree']|Literal['ast']|Literal['query'] = 'query'

while True :
    print()
    user_input = input(f' {mode} > ')

    try :

        document = list(tokenizer(user_input))
        
        match document :
            case [(_, 'mode', _), (_, ('parsetree' | 'ast' | 'query') as newmode, _)] :
                mode = newmode
                continue
        
        
        recognizer = Recognizer(
            document=document,
            real_string_input=user_input
        )
        recognizer.earley_recognize()

        parsetree = Parser(document=document, items=recognizer.state_sets).create_tree()

        if mode == 'parsetree' :
            parsetree.prettyprint()
            continue

        ast = RelationalTreeReducer().ast(parsetree)

        if mode == 'ast' :
            pprint(ast)
            continue

        result = ast.eval([], example_relations)

        if isinstance(result, Relation) :
            result.prettyprint()
        else :
            pprint(result)

    except (SyntaxError, TypeError, ValueError, NameError) as e :
        print(f"({e.__class__.__name__}) {str(e)}")
