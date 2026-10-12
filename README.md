# Artifical World
Create small-scaled gridded data along with ODE equations that can be simulated.

Roughly speaking this creates a *model configuration* that looks like this:

```json
{
  name: name,
  width: width,
  height: height,
  equations: [...],
  variables: [...]
}
```

That can feed into a python ODE simulatr/solver in JAX.


## Setup
```
# Install root deps/utils
npm install

# Install client deps
cd client && npm install

# Install server deps
cd server && pip3 install -r requirements.txt
```


## Run artifical world
```
npm run dev
```
Goto http://localhost:5173


## ODE Scripts
The underlying script is **server/ode_simulator.py**, this creates a \<WorldName\>_simluation.json
```
python3 ode_simulator.py worlds/PP.json --steps 50 --dt 0.1
```

Given a simulation json file, create an animated gif.
```
python3 visualize_simulation.py PP_simulation.json -o simulation.gif --fps 15
```
