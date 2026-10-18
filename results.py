import matplotlib.pyplot as plt
from lazyportfolio import lazyports
from idealportfolio import idealport
from performance import Performance, SPYport
from treasuryyields import rf

lazyresults: dict[float, Performance] = dict()

for delta in lazyports:
    lazy, history = lazyports[delta]
    lazyresults[delta] = Performance(lazy, rf)

spyresult = Performance(SPYport[0], rf)
idealresult = Performance(idealport[0], rf)