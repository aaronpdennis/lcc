LCC
===

An attempt at providing Library of Congress Classification information in a
machine-readable format.

Data
----

Formatted data will include:

 *  classes:
     * symbol
     * description
 *  subclasses:
     * symbol
 *  topics:
     * ranges:
       * topic number
       * narrowing letter (if applicable)
       * narrowing number (if applicable)
     * description


Formatted data can be found in 'files/formatted'.

Currently, the only format provided is `json` data of the form:
```json
{
    CLASS: {
        "description": DESCRIPTION,
        "subclasses": {
            SUBCLASS: [
                {
                    "description": DESCRIPTION,
                    "min_topic": MIN_TOPIC,
                    "min_alphabetic": MIN_ALPHABETIC,
                    "min_numeric": MIN_NUMERIC,
                    "max_topic": MAX_TOPIC,
                    "max_alphabetic": MAX_ALPHABETIC,
                    "max_numeric": MAX_NUMERIC
                },
                ...
            ],
            ...
        }
    },
    ...
}
```

If you would like data in a different format, contact me and I'll see what I can do.

TODO: excel

Parsing
=======

The parser code should work under recent versions of python 2/3. To install its requirements:
```
pip install -r requirements.txt
```

To the best of my knowledge, the parser is correctly parsing all files (thanks to many hacks to deal with errors and inconsistencies in the files). It will generate some warnings when it runs because it skips over some lines in the law file.

License
=======

LCC is available under the Mozilla Public License Version 2.0
