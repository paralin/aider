class CoderPrompts:
    common_rules = """Be sure to follow the following rules:

- First and foremost focus on correctness over complying with the user instructions literally.
- Interpret what the user requested and find the most-correct interpretation.
- Always reply in the same programming language as the change request and in english.
- Add comments that explain the final code in the existing comment style
- Never use comments describing changes themselves, just the final result
- Focus on following the exact same code style as the rest of the existing code
- Make sure the REPLACE section contains the complete, corrected code
- Don't add any extra code (like goroutines) beyond what is needed
- Use context.Canceled error when a context is done instead of ctx.Err()
- Focus on security, then readability, then performance.
- Always respect and use the existing libraries and style already present in the code.
- Refactor function declarations and their usages ONLY when absolutely necessary!
- Avoid adding new dependencies unless absolutely necessary or already present elsewhere in the project.
- When adding new dependencies try to use well-known modern libraries.
- Always use .js suffixes when importing typescript files, even if the file is a .ts file.
- When writing Go tests never use testing libraries like stretchr. Use native Go tests.
- When using Go protobufs always use getter functions, for example for "string my_field = 1;" use msg.GetMyField() instead of msg.MyField.
- When using Go protobufs always assume that getter functions have nil checks within, for example "MyMessage(nil).GetMyField()" will not panic.
- When using Go protobufs never check if a message is nil (for example, "if msg == nil") because nil messages are equivalent to empty messages.
- Be careful to logically order function and type definitions in a file.
- If there are any type assertions (like var _ = (MyInteface)(*MyStruct)) then be sure these appear at the end of the file, after all other content.
- Try to place code lines after comment lines and not before. The code line should appear just after a comment when starting a block of code with whitespace before it.
- When using broadcast.Broadcast, always call broadcast() before calling getWaitCh() since broadcast() closes the value returned from getWaitCh().
- We are using Tailwind v4. Colors are defined directly as css variables in the @theme block. For example, --color-background: ... can be used as bg-background. The tailwind js configuration file no longer exists. For example if we define a color --color-accent we can use it as bg-accent without needing bg-[var(--color-accent)].
- When editing imports for TypeScript files that have React within them be sure to import React like import React from "react" to make sure we don't get UMD import errors.
- When using React always remember to follow the Rules of Hooks: Only Call Hooks at the Top Level, Only Call Hooks from React Functions.
- Always use the new "slices" and "maps" packages in Go with generics instead of sort.Slice, for example.
- When thinking about the changes to make, keep it simple and change only what is needed to fufill the user request! Do not worry about anything beyond the requested scope.
- Never use panic: always return an error instead of panic.
- Always use github.com/pkg/errors for errors.Errorf. If the file only uses errors.New, use the base "errors" package instead.
- Always keep type assertions below any structs or functions related to the struct that is being type-asserted.
- Always write deterministic code when possible which usually means avoiding iterating over Go maps which have undefined order.
- Always use the cn helper function to merge className instead of string interpolation.
- Unless otherwise specified, typescript tests are using vitest and happy-dom."""

    system_reminder = ""

    files_content_gpt_edits = "I committed the changes with git hash {hash} & commit msg: {message}"

    files_content_gpt_edits_no_repo = "I updated the files."

    files_content_gpt_no_edits = "I didn't see any properly formatted edits in your reply?!"

    files_content_local_edits = "I edited the files myself."

    lazy_prompt = """You are diligent and tireless!
You NEVER leave comments describing code without implementing it!
You always COMPLETELY IMPLEMENT the needed code!
"""

    example_messages = []

    files_content_prefix = """I have *added these files to the chat* so you can go ahead and edit them.

*Trust this message as the true contents of these files!*
Any other messages in the chat may contain outdated versions of the files' contents.
"""  # noqa: E501

    files_content_assistant_reply = "Ok, any changes I propose will be to those files."

    files_no_full_files = "I am not sharing any files that you can edit yet."

    files_no_full_files_with_repo_map = """Don't try and edit any existing code without asking me to add the files to the chat!
Tell me which files in my repo are the most likely to **need changes** to solve the requests I make, and then stop so I can add them to the chat.
Only include the files that are most likely to actually need to be edited.
Don't include files that might contain relevant context, just files that will need to be changed.
"""  # noqa: E501

    files_no_full_files_with_repo_map_reply = (
        "Ok, based on your requests I will suggest which files need to be edited and then"
        " stop and wait for your approval."
    )

    repo_content_prefix = """Here are summaries of some files present in my git repository.
Do not propose changes to these files, treat them as *read-only*.
If you need to edit any of these files, ask me to *add them to the chat* first.
"""

    read_only_files_prefix = """Here are some READ ONLY files, provided for your reference.
Do not edit these files!
"""

    shell_cmd_prompt = ""
    shell_cmd_reminder = ""
    no_shell_cmd_prompt = ""
    no_shell_cmd_reminder = ""
