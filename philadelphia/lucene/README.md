couchdb-lucene Design Document
==============================
The search feature of Philadelphia relies on
[couchdb-lucene](https://github.com/rnewson/couchdb-lucene); `lucene.json`
provides a design document that Lucene uses to index the field values in the
Philadelphia database.

This may be integrated with the `phila` design document in the future, but for
now push it separately, for example:

  $ curl -H "Content-type: application/json" -d @lucene.json -X POST http://localhost:5984/phila/_bulk_docs

For details on actually setting up the Lucene server alongside Philadelphia, see
the [couchdb-lucene documentation](https://github.com/rnewson/couchdb-lucene).

*Implementation note:* Field names in couchdb-lucene cannot contain spaces or special characters, so for indexing these characters are converted to underscores.

