AnyField
********

**Note**, this module is in **experimental** stage

This module provides *SField* class which is ised to avaoid lambdas
there where function of one argument is required to be applied to
multiple items Examples of such cases could be functions like: -
sorted - filter - map - etc

Also this module provides shortcuts (already built SField instances),
that could be starting point of SField expressions. They are: SF, F
Both are same.

For example::

   import requests
   from anyfield import F, SView
   data = requests.get('https://api.github.com/repos/vmg/redcarpet/issues?state=closed')
   data = data.json()
   view = SView(F['id'],
                F['state'],
                F['user']['login'],
                F['title'][:40],
   )
   for row in view(data):
       print(row)

Will result in::

   [121393880, u'closed', u'fusion809', u'Rendering of markdown in HTML tags']
   [120824892, u'closed', u'nitoyon', u'Fix bufprintf for Windows MinGW-w64']
   [118147051, u'closed', u'clemensg', u'Fix header anchor normalization']
   [115033701, u'closed', u'mitchelltd', u'Unicode headers produce invalid anchors']
   [113887752, u'closed', u'Stemby', u'Definition lists']
   [113740700, u'closed', u'Stemby', u'Multiline tables']
   [112952970, u'closed', u'im-kulikov', u"recipe for target 'redcarpet.so' failed"]
   [112494169, u'closed', u'mstahl', u'Unable to compile native extensions in O']
   [111961692, u'closed', u'reiz', u'Adding dependency badge to README']
   [111582314, u'closed', u'jamesaduke', u'Pre tags on code are not added when you ']
   [108204636, u'closed', u'shaneog', u'Push 3.3.3 to Rubygems']
