


import pandas as pd
import numpy as np
import matplotlib.pylab as plt

#import nltk.tokenize
#from sklearn.feature_extraction.text import TfidfVectorizer, HashingVectorizer, TfidfTransformer
from sklearn import cross_validation as c_v #,neighbors, datasets, grid_search
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report

# import database connector
from db.beeradcn import Beerad
from reviewvectorizer import ReviewTfidf, ReviewCountVec

def pth(f):
  return 'src/vocab/' + f

# get list of top #num styles ranked by review count
def get_styles(cur,num=5):
  qry = """
    select style_id
    from reviewctbystyle
    order by rev_ct desc
    limit %s """
  
  q_res = cur.execute(qry, (num,))
  return [int(r[0]) for r in cur.fetchall()]


# get #num reviews for a given style_id
def get_revs(cur,style_id,num=30000):
  qry = """
        select be.style_id, r.beer_id, r.review
        from reviews r inner join beers be
            on r.beer_id = be.id
        where be.style_id = %s
            and char_length(replace(trim(review),'\n','')) > 30
        limit %s """
    
  q_res = cur.execute(qry, (style,num))
  dt = cur.fetchall()
  return pd.DataFrame.from_records((r for r in dt), columns=['style_id','beer_id','review'])
  

# compute and plot confusion matrix
import pylab as pl
from sklearn.metrics import confusion_matrix
def plot_confusion(y, pred):
  cm = confusion_matrix(y, pred)
  pl.matshow(cm)
  pl.title('Confusion matrix')
  pl.colorbar()
  pl.ylabel('True label')
  pl.xlabel('Predicted label')
  pl.show()
  

def print_best_worst_feat(tfidf, num):
  idf = tfidf._tfidf.idf_
  w_lst = zip(tfidf.get_feature_names(), idf)
  w_lst.sort(key = lambda x: -x[1])
  for i in xrange(num):
    print "%s\t%s" % (w_lst[i], w_lst[-num+i])
  

# train NB style predictor and make test prediction
def fit_and_predict(x_train, y_train, x_test, **kwargs):
  tfidf = ReviewTfidf(**kwargs)
  trans = tfidf.fit_transform(x_train)

  print_best_worst_feat(tfidf, 10)

  nb = MultinomialNB()
  nb.fit(trans, y_train)
  
  # transform test set
  test_t = tfidf.transform(x_test)
    
  # predict class
  pred = nb.predict(test_t)
  
  return pred



def shuffle_ix(df):
  nix = np.random.permutation(df.index)
  df = df.reindex(index=nix, copy=False)
  return df.reset_index().drop('index',1)


# begin script
# load reviews by style
with Beerad() as dbc:
  cur = dbc.cursor()
  
  styles = get_styles(cur)
  
  revs = { s: pd.DataFrame() for s in styles }
  for style in styles:
    print 'Retrieving reviews for style %s' % style
    revs[style] = get_revs(cur, style)
    
    # shuffle
    revs[style] = shuffle_ix(revs[style])
    # create 10 review docs per beer
    revs[style]['rev_doc'] = revs[style].index % 10
    revs[style] = revs[style].groupby(['style_id', 'beer_id', 'rev_doc']).apply(lambda x: ' '.join(x['review']))
    print 'Grouped Style Beer Docs %s' % len(revs[style].index)
  cur.close()


# form single consolidated dataset
revs = pd.concat([revs[s] for s in styles])
revs = revs.reset_index()   # move style, beer, rev_doc index to cols
revs = shuffle_ix(revs)     # shuffle on new numerical index
revs.columns = ['style_id', 'beer_id', 'rev_doc', 'review']

n = len(revs.index)
print 'Total Beer Review Docs: %s' % n

kf = c_v.StratifiedKFold(revs['style_id'], n_folds = 10)

from db.basewordcts import BaseWordFreq
baseline = BaseWordFreq()
baseline.load_all()


# run model
mod_ct = 0
for train, test in kf:
  mod_ct += 1
  print '\nStart model %s' % mod_ct
  
  # store vocab
  vocab = np.array('hop')
  
  # param settings
  max_features=None
  ngram_range=(1,2)
  min_df=0.05
  max_df=0.8
  
  # build style specific vocabulary
  for style in styles:
    
    print '\nVectorizing reviews for style %s' % style
  
    # build review vectorizer
    tfidf = ReviewTfidf(
      max_features=max_features,
      min_df=min_df,
      max_df=max_df,
      binary=True,
      stop_words=baseline.keys())
    
    x_train = revs.ix[train]
    x_train = x_train[x_train['style_id'] == style]
    tfidf.fit_transform(x_train['review'].values.ravel())
    
#    with open(pth('s-{0}-r-{1}.txt'.format(style, mod_ct)), 'w') as vo:
#      idf = tfidf._tfidf.idf_
#      w_lst = zip(tfidf.get_feature_names(), idf)
#      w_lst.sort(key = lambda x: -x[1])
#      for w in w_lst:
#        vo.write("{0},{1}\n".format(w[0],w[1]))
    
    print 'Storing vocabulary'
    vocab = np.unique(np.append(vocab, tfidf.get_feature_names()))
#    feat = tfidf.get_feature_names()
#    for fi in feat:
#      if fi not in baseline.keys():
#        vocab = np.append(vocab, fi)
#    vocab = np.unique(vocab)
    print 'Vocabulary size %s' % len(vocab)


  # extract features with the full vocabulary
  print '\nTraining with full vocabulary'
  
  # build train and test dataframe with all reviews
  full_train, full_test = revs.ix[train], revs.ix[test]
  y_test = full_test[["style_id"]].values.ravel()
  y_pred = fit_and_predict(full_train[["review"]].values.ravel(), # x-train
            full_train[["style_id"]].values.ravel(),  # y-train
            full_test[["review"]].values.ravel(),     # x-test
            max_features=max_features,
            min_df=min_df,
            max_df=max_df,
            binary=True,
            vocabulary=vocab)
  
  print 'Classification Report for model %s' % mod_ct
  print classification_report(y_test, y_pred)
  print confusion_matrix(y_test, y_pred)
  print 'Full vocabulary', vocab, '\n'
  
  if mod_ct == 1:
    break






