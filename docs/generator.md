# Generator
The generator is used for generating inputs. Solutions are then run and judged on those.

## Generator type
There are currently 3 generator types available:
- pisek-v1
- cms-old
- opendata-v1

However we strongly recommend using the pisek-gen type
for better debugging and easy conversion between open data and closed data tasks.

## Terminology
There are two requirements for generators:
- Generators **must** be deterministic. (For the same arguments, it should generate the same input(s).) 
- If a generator takes a seed as an argument, the generator **should** respect the seed. (For different seeds
  it should generate different inputs.) This can be disabled in the `[checks]` section, but be careful.

## Pisek-v1
### Listing inputs
When run without arguments it should list all inputs it can generate in the following format: 
```
input_name key1=value1 key2=value2
```
Where `input_name` is the name of the given input. The input will be generated into the file
`[input_name]_[seed].in` or `[input_name]` (depending whether the input is seeded).
This is followed by any number of key=value pairs separated by spaces.
The following keys are supported:

| Key    | Meaning                                        | Value type | Default value |
| ------ | ---------------------------------------------- | ---------- | ------------- |
| repeat | How many times should this input be generated? | int        | 1             |
| seeded | Is this input generated with a random seed?    | bool       | true          | 

If the input is not seeded, repeat must be 1.

For example:
```
01_tree
02_random_graph repeat=10
02_complete_graph seeded=false
```

### Generating inputs
The generator is then repeatedly asked to generated the input `input_name` from
the inputs list.

If `input_name` is seeded the generator is run with:
```
./gen [input_name] [seed]
```
Where `seed` is a hexadecimal number. The generator must be deterministic and
respect the seed.

If `input_name` is unseeded the generator is called with  
```
./gen [input_name]
```
The generator must be deterministic.

In either case, the generator should print the input to its stdout. 

## Cms-old
The generator is run with:
```
./gen [directory]
```

The generator should generate all input files to this directory. The generator must be deterministic.

## Opendata-v1
The generator is run:
```
./gen [test] [seed]
```

The generator should generate the input for this test to its stdout. The generator must be deterministic
and respect the given seed.

(Please note that the generator can generate only one input for each test.)
