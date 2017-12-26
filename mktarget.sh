#!/bin/bash

mkdir -p scripts/$1
cat <<EOF > scripts/$1/BUILD
python_binary(
  name="$1",
  source="$1.py",
  dependencies=[

  ],
)
EOF
