# Throwaway spike code (S-04): TLC -tool output -> JSON trace (list of {n, action, vars}).
import json, re, sys
text = open(sys.argv[1]).read()
states = []
for body in re.findall(r"@!@!@STARTMSG 2217:4 @!@!@\n(.*?)\n@!@!@ENDMSG 2217 @!@!@", text, re.S):
    head, _, rest = body.partition("\n")
    number, action = re.match(r"(\d+): <(.*)>", head).groups()
    variables = dict(re.findall(r"^/\\ (\w+) = (.*)$", rest, re.M))
    states.append({"n": int(number), "action": action, "vars": variables})
json.dump({"violated": re.findall(r"Invariant (\w+) is violated", text), "trace": states}, sys.stdout, indent=1, ensure_ascii=False)
