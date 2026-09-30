from parser import Relation

employees = Relation(
    cols=['id', 'name', 'departmentid', 'managerid'],
    data=[
        [1, 'a', 'd1', 2],
        [2, 'b', 'd1', -1],
        [3, 'c', 'd2', 2],
    ]
)

departments = Relation(
    cols=['id', 'name'],
    data=[
        ['d1', 'finance'],
        ['d2', 'marketing']
    ]
)

example_relations = {
    "employees": employees,
    "departments": departments
}