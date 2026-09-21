from dataclasses import dataclass, field
from typing import Any, Callable

type Terminal = Callable[[str], bool]
type grammartype = dict[str, list[list[str | Terminal]]]


START_SYMBOL = "^"

# [*literal_terminals("if"), "expr", *literal_terminals("then")]

from functools import wraps

def hook_str_of_function(func:Terminal, display_text:str):
    setattr(func, "__str__", lambda : display_text)
    return func

def literal(s):
    assert len(s) == 1
    func = lambda x : x == s
    return hook_str_of_function(func, s)

def literal_terminals(s:str):
    return [hook_str_of_function(literal(character), character) for character in s]

def any_terminal_in(s:str):
    func =  lambda x : x in s
    return hook_str_of_function(func, s)

arithmetic_grammar = {
    START_SYMBOL: [["sum"]],
    "sum": [["product"], ["product", literal("+"), "sum"]],
    "product": [["factor"], ["factor", literal("*"), "product"]],
    "factor": [["number"], [literal("("), "sum", literal(")")]],
    "number": [["digit"], ["number", "digit"]],
    "digit": [[any_terminal_in("0123456789")]]
}

simple_arithmetic_grammar = {
    START_SYMBOL: [["sum"]],
    "sum": [["number"], [literal("("), "sum", literal(")")], ["sum", literal("+"), "sum"]],
    "number": [["digit"], ["number", "digit"]],
    "digit": [[any_terminal_in("0123456789")]]
}

def is_token_terminal(token: str | Terminal | None):
    return type(token) != str

@dataclass
class ParsingItem:
    start:int
    rule: list[str | Terminal]
    goal: str
    progress:int = 0

    @property
    def next_token(self):
        return self.rule[self.progress] if self.progress < len(self.rule) else None

    @property
    def is_completed(self) -> bool:
        return self.progress == len(self.rule)
    

    @property
    def action_needed(self):
        if self.is_completed : return 'complete'
        
        waiting_on_terminal = is_token_terminal(self.next_token)

        return 'scan' if waiting_on_terminal else 'predict'

    @staticmethod
    def token_to_str(token: str | Terminal):
        return token.__str__()

    def __str__(self) -> str:
        return f"{self.goal} -> {' '.join(map(self.token_to_str, self.rule[:self.progress]))} . {' '.join(map(self.token_to_str, self.rule[self.progress:]))}  ({self.start})"

@dataclass
class Recognizer:

    document: str
    grammar: grammartype = field(default_factory=lambda : simple_arithmetic_grammar)
    state_sets: list[list[ParsingItem]] = field(default_factory=lambda : [])

    def item_already_exists(self, i, new_item:ParsingItem):
        return any(
            other.rule == new_item.rule and other.progress == new_item.progress and other.start == new_item.start
            for other in self.state_sets[i]
        )

    def repr_state_sets(self) -> str :
        return "\n".join(
            f"=== {i} ===\n{'\n'.join(map(str, state_set))}"
            for i, state_set in enumerate(self.state_sets)
        )

    def complete(self, i, j):

        item:ParsingItem = self.state_sets[i][j]
        assert item.is_completed

        for other_item in self.state_sets[item.start] :

            if other_item.next_token != item.goal : continue

            next_item = ParsingItem(
                start = other_item.start,
                progress = other_item.progress + 1,
                rule = other_item.rule,
                goal = other_item.goal
            )

            if self.item_already_exists(i, next_item) : continue

            self.state_sets[i].append(next_item)

    def predict(self, i, j):

        item:ParsingItem = self.state_sets[i][j]
        next_token = item.next_token
        assert isinstance(next_token, str)

        child_rules = self.grammar[next_token]

        for child_rule in child_rules :

            new_item = ParsingItem(rule=child_rule, goal=next_token, start=i)
            if self.item_already_exists(i, new_item) : continue

            self.state_sets[i].append(new_item)

    def scan(self, i, j):
        item:ParsingItem = self.state_sets[i][j]
        terminal_predicate = item.next_token
        assert isinstance(terminal_predicate, Callable)

        if i + 1 >= len(self.state_sets) or i >= len(self.document) : return

        next_symbol_in_stream = self.document[i]

        if terminal_predicate(next_symbol_in_stream) :
            next_item = ParsingItem(
                start = item.start,
                progress = item.progress + 1,
                rule = item.rule,
                goal = item.goal
            )

            if self.item_already_exists(i+1, next_item) : return
            self.state_sets[i+1].append(next_item)

    def earley_recognize(self):

        self.state_sets = [
            [] for x in self.document
        ] + [[]]

        self.state_sets[0] = [
            ParsingItem(rule=x, start=0, goal=START_SYMBOL)
            for x in self.grammar[START_SYMBOL]
        ]

        # print(
        #     self.repr_state_sets()
        # )

        for i in range(len(self.document) + 1) :
            j = 0
            while j < len(self.state_sets[i]):
                print(self.state_sets[i][j].action_needed)
                match self.state_sets[i][j].action_needed:
                    case 'predict' :
                        self.predict(i, j)
                    case 'scan' :
                        self.scan(i, j)
                    case 'complete' :
                        self.complete(i, j)
                j += 1

        was_parse_successful = any(
            item.start == 0 and item.is_completed for item in self.state_sets[-1]
        )

        def remove_all_incomplete_items():

            for i, state_set in enumerate(self.state_sets) :
                self.state_sets[i] = [
                    item
                    for item in state_set
                    if item.is_completed
                ]

        remove_all_incomplete_items()
        self.state_sets = Parser.invert_items(self.state_sets)
        print(
            self.repr_state_sets()
        )

        return was_parse_successful

@dataclass
class InvertedItem(ParsingItem):
    end: int = 0

    @staticmethod
    def from_item(item:ParsingItem, i:int):
        assert item.progress == len(item.rule)
        return InvertedItem(
            start=i,
            end=i,
            goal=item.goal,
            rule=item.rule,
            progress=len(item.rule)
        )

@dataclass
class Parser:

    @staticmethod
    def invert_items(items: list[list[ParsingItem]]) -> list[list[InvertedItem]]:
        out = [[] for x in items]

        for i, state_set in enumerate(items):
            for item in state_set :
                out[item.start].append(InvertedItem.from_item(item, i))

        return out

r = Recognizer(document="1+2+3+4")

r.earley_recognize()