## For demo copy and paste 

### SIR demo
```
dS/dt = -beta * S * I / N
dI/dt = beta * S * I / N - gamma * I
dR/dt = gamma * I
```

### Predator Prey
```
dRabbits/dt = RabbitGrowth * Rabbits - PredationRate * Rabbits * Wolves
dWolves/dt = ReproductionRate * Rabbits * Wolves - WolfDeathRate * Wolves
```

### Movement rate generator based on land
```
function callback(i, j, world) {
  const land = world.variables.find(d => d.name === 'land');
  const data = land.data;
  const rows = data.length;
  const cols = data[0]?.length ?? 0;

  const isWater = (r, c) =>
    r < 0 ||
    r >= rows ||
    c < 0 ||
    c >= cols ||
    data[r]?.[c] === 'water';

  if (isWater(i, j)) {
    return {
      n: 0, s: 0, e: 0, w: 0,
      ne: 0, nw: 0, se: 0, sw: 0
    };
  }

  return {
    n:  isWater(i - 1, j)     ? 0 : 0.1,
    s:  isWater(i + 1, j)     ? 0 : 0.1,
    e:  isWater(i, j + 1)     ? 0 : 0.1,
    w:  isWater(i, j - 1)     ? 0 : 0.1,

    ne: isWater(i - 1, j + 1) ? 0 : 0.1,
    nw: isWater(i - 1, j - 1) ? 0 : 0.1,
    se: isWater(i + 1, j + 1) ? 0 : 0.1,
    sw: isWater(i + 1, j - 1) ? 0 : 0.1
  };
}
```
