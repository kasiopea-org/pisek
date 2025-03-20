program FindMaximum;
var
  N, i, max, num: integer;
begin
  readln(N);
 
  read(num);
  max := num;

  for i := 2 to N do
  begin
    read(num);
    if num > max then
      max := num;
  end;

  writeln(max);
end.
