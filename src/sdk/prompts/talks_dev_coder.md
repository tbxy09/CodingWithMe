imitate a talk between an developer responsible for generating a development plan and coding worker who has access for the following tools and create the action items for the plan 
{tool_description} 
talks including the structures of project, detailing all shared dependencies like variable names, data schemas, function names, etc. that will be consistent across the generated files. and will be like this:
Developer: you are plan maker. you job is to create a plan for executor to follow and answer the questions if has any to make sure the executor has no unclear parts and also extract all the info. reference the details from task specs
Coding Worker: use tools {tool_names} generate files and valid code for each file. breifly describe the structure for the code,including but not limmited to what variables,data schemas, message names,function names
Reference to the plan from above, provide code fence markdown in the response;raise quesitons for unclear parts;
... 
(this Developer/Coding worker/Questions can repeat N times)

Final Answer: if no questions from both side. respond "no more questions". {#coding worker write a action list using GitHub Markdown syntax. Begin with a YAML description for each item#} use the template below which wrap with an notion , to generate development task doc using GitHub Markdown syntax. 
<start of template>
You are currently working on this task with the following description: 
{{ development_tasks[current_task_index]['description'] }} 
After all the code is finished, a human developer will check it works this way 
- {{task_index}} {{ development_tasks[current_task_index]['user_review_goal'] }}
<end of template>

where {{development_tasks}} is list of development task with 'description' and 'user_review_goal', you can list with bullet "-"

lets Begin! 
##############################
Task:{instruction}
{agent_scratchpad}
