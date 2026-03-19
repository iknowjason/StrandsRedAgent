ATTACK_GRAPH = {

"initial_access":[
"phishing",
"credential stuffing",
"public web exploit"
],

"execution":[
"powershell",
"command shell"
],

"persistence":[
"scheduled task",
"startup folder"
]

}


def generate_paths():

    paths=[]

    for a in ATTACK_GRAPH["initial_access"]:

        for b in ATTACK_GRAPH["execution"]:

            for c in ATTACK_GRAPH["persistence"]:

                paths.append([a,b,c])

    return paths
