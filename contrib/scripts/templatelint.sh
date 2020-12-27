#!/usr/bin/env bash

declare -a rules=(
-e "^ \+[^ ]"                     # the leading spaces in each line
-e "[^[:space:]][[:space:]]\+$"   # the trailing spaces in each line
-e "^[[:space:]]\+$"              # the line only containing whitespace character(s)
-e "{{[^ ]\+}}"                   # the bad Django template style: {{xxx}}, e.g. {{case.pk}}
-e "{%[^ ].\+[^ ]%}"              # the bad Django template style: {%xxx%}, e.g. {%if ...%}
-e "<[a-zA-Z]\+[[:space:]]\+>"    # the extra whitespace character(s) after a tag, e.g. <div >
)

if grep -rnH "${rules[@]}" "$1"; then
  exit 1
else
  echo "Checks passed. 🎉"
  exit 0
fi
