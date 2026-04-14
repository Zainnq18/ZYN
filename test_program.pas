! Sample program in the Option-1 language
program factorial;

var
    n : integer;
    result : integer;

function computeFact(x : integer) : integer;
var
    f : integer;
begin
    if x <= 1 then
        f := 1
    else
        f := x * computeFact(x - 1);
    computeFact := f
end;

begin
    write('Enter a number: ');
    read(n);
    result := computeFact(n);
    write('Factorial = ');
    write(result)
end.
