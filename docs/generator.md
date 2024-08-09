# Generator
Generator is used for generating inputs. Solutions are then run and judged on those.

## Generator format
There are currently 3 generator formats available:
- pisek-gen
- cms-old
- opendata-v1

However we strongly recommend using pisek-gen format
for better debugging and easy conversion between open data and closed data tasks.

## Terminology
We have two types of requirements for generators:
- Generators **must** be deterministic. (For same arguments, it should generate same input(s).) 
- If generator takes seed as argument, generator **should** respect seed. (For different seeds
  it should generate different inputs) This can be disabled in `[checks]` section, but be careful.

## Pisek-gen
### Listing inputs
When run without arguments it should list all inputs it can generate in the following format: 
```
input_name key1=value1 key2=value2
```
Where `input_name` is name of given input. The input will be generated into file
`[input_name]_[seed].in` or `[input_name]` (depending whether input is seeded).
This is followed by any number of key=value pairs separated by spaces.
The following keys are supported:

| Key    | Meaning                                       | Value type | Default value |
| ------ | --------------------------------------------- | ---------- | ------------- |
| repeat | How many times this input should be generated | int        | 1             |
| seeded | Is this input generated depending on seed?    | bool       | true          | 

If input is seeded, repeat must be 1.

For example:
```
01_tree
02_random_graph repeat=10
02_complete_graph seeded=false
```

### Generating inputs
Generated is then repeatedly asked to generated input `input_name` from
inputs list.

If `input_name` is seeded generator is run:
```
./gen [input_name] [seed]
```
Where `seed` is a hexadecimal number. Generator must be deterministic and
respect seed.

If `input_name` is unseeded generator is  
```
./gen [input_name]
```
Generator must be deterministic.

In either case, generator should print the input to it's stdout. 

## Cms-old
Generator is run:
```
./gen [directory]
```

Generator should generate all input files to this directory. Generator must be deterministic.

## Opendata-v1
Generator is run:
```
./gen [subtask] [seed]
```

Generator should generate input for this subtask to it's stdout. Generator must be deterministic
and respect given seed.

(Please note that generator can generate only one input for each subtask.)
