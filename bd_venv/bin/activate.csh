# This file must be used with "source bin/activate.csh" *from csh*.
# You cannot run it directly.
# Created by Davide Di Blasi <davidedb@gmail.com>.
# Ported to Python 3.3 venv by Andrew Svetlov <andrew.svetlov@gmail.com>

alias deactivate 'test $?_OLD_VIRTUAL_PATH != 0 && setenv PATH "$_OLD_VIRTUAL_PATH" && unset _OLD_VIRTUAL_PATH; rehash; test $?_OLD_VIRTUAL_PROMPT != 0 && set prompt="$_OLD_VIRTUAL_PROMPT" && unset _OLD_VIRTUAL_PROMPT; unsetenv VIRTUAL_ENV; unsetenv VIRTUAL_ENV_PROMPT; test "\!:*" != "nondestructive" && unalias deactivate'

# Unset irrelevant variables.
deactivate nondestructive

setenv VIRTUAL_ENV "/Users/daniel/Desktop/Python/BuDoDjango/bd_venv"

set _OLD_VIRTUAL_PATH="$PATH"
setenv PATH "$VIRTUAL_ENV/bin:$PATH"


set _OLD_VIRTUAL_PROMPT="$prompt"

if (! "$?VIRTUAL_ENV_DISABLE_PROMPT") then
    set prompt = "(bd_venv) $prompt"
    setenv VIRTUAL_ENV_PROMPT "(bd_venv) "
endif

alias pydoc python -m pydoc

# Custom alias for pip freeze that puts packages in dev_only_packages.toml into requirements/dev.txt and all others into requirements/base.txt
alias pipfreeze='if [ ! -f "./dev_only_packages.toml" ]; then echo "Error: dev_only_packages.toml not found"; exit 1; fi && \
mkdir -p ./budo_database/requirements && \
python3 -m pip freeze | grep -v -f <(sed "/^#/d; /^$/d; s/^/^/" ./dev_only_packages.toml | sed "s/$/==/") > ./budo_database/requirements/base.txt && \
python3 -m pip freeze | grep -f <(sed "/^#/d; /^$/d; s/^/^/" ./dev_only_packages.toml | sed "s/$/==/") > ./budo_database/requirements/dev.txt'
rehash
