import numpy as np

def metrics(y,pred):
    y=np.asarray(y,dtype=bool); pred=np.asarray(pred,dtype=bool)
    if y.shape!=pred.shape or y.size==0: raise ValueError('Invalid evaluation arrays')
    tp=int(np.sum(y&pred)); tn=int(np.sum(~y&~pred)); fp=int(np.sum(~y&pred)); fn=int(np.sum(y&~pred))
    div=lambda a,b:a/b if b else 0.0
    pos_f1=div(2*tp,2*tp+fp+fn); neg_f1=div(2*tn,2*tn+fp+fn)
    return dict(Accuracy=div(tp+tn,len(y)),Precision=div(tp,tp+fp),Recall=div(tp,tp+fn),
                Macro_F1=(pos_f1+neg_f1)/2,False_Positive_Rate=div(fp,fp+tn),TP=tp,TN=tn,FP=fp,FN=fn)

def delay(t,pred,onset):
    hit=np.asarray(t)[(np.asarray(t)>=onset)&np.asarray(pred,dtype=bool)]
    return float(hit[0]-onset) if len(hit) else None
