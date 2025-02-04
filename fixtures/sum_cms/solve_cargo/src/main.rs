use std::{
    error::Error,
    io::{stdin, stdout, Read, Write},
    str::FromStr,
};

fn main() -> Result<(), Box<dyn Error>> {
    let mut input = String::new();
    stdin().lock().read_to_string(&mut input)?;

    let sum = input
        .split_whitespace()
        .map(i64::from_str)
        .sum::<Result<i64, _>>()?;

    let mut output = stdout().lock();
    // Dump as JSON, just to show it's possible to use a library.
    serde_json::to_writer(&mut output, &sum)?;
    writeln!(output)?;

    Ok(())
}
