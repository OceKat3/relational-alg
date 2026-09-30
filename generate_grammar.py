from parser import relational_algebra_grammar, is_token_terminal, identifier, number

ebnf = "\n\n".join(
    f"{goal} = " + '\n     | '.join(
        ' '.join(
            f'"{token.__str__()}"' if 
            (not isinstance(token, str) and token not in [identifier, number]) 
            else token.__str__()
            for token in option
        )
        for option in rule
    )
    for goal, rule in relational_algebra_grammar.items()
)

print(ebnf)

# python generate_grammar.py > GRAMMAR.md