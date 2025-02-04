import sys
import math
import numpy as np

states = np.array(['H', 'C'])
features = np.array(['1', '2', '3'])

# labels       = np.array([1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1])
# observations = np.array([1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1, 1])
labels       = np.array([1, 0, 0])
observations = np.array([1, 2, 3])

t = len(observations)

def one_hot(target, num_classes):
  v = np.zeros(num_classes)
  v[target] = 1
  return v

def create_dataset():
  X = np.zeros((3, t))
  Y = np.zeros((2, t))
  for i in range(t):
    X[:,i] = one_hot(observations[i] - 1, 3)
    Y[:,i] = one_hot(labels[i], 2)
  return X, Y

class InputLayer():
  def __init__(self, n_x, n_y, t):
    self.n_x = n_x
    self.n_y = n_y
    self.t = t
    self.X = None

    np.random.seed(1)
    self.Wx  = np.random.randn(n_y, n_x)

  def set_input(self, X):
    self.X = X

  def propagate(self):
    return np.dot(self.Wx, self.X)

  def backpropagate(self, dxt, learning_rate=0.01):
    dx = np.dot(dxt, self.X.T)
    self.Wx -= learning_rate * np.clip(dx , -5.0, 5.0, dx)

class Crf():
  def __init__(self, n_y, t, input_layer):
    self.n_y = n_y
    self.t = t

    self.input_layer = input_layer

    np.random.seed(2)
    # self.Wyy = np.random.randn(n_y, n_y)
    self.Wyy = np.ones((n_y, n_y))

  def score(self, xt):
    return np.exp(self.Wyy + xt.T)

  def neg_log_likelihood(self, X, Y, partition_value):
    value = 0
    prev_y = np.zeros((self.n_y, 1))
    for i in range(self.t):
      xt = X[:,i,np.newaxis]
      yt = Y[:,i,np.newaxis]
      score = self.Wyy + xt.T
      value += np.dot(np.dot(score, prev_y).T, yt).item()
      prev_y = yt
    return -(value - np.log(0.1 + partition_value))

  def propagate(self, X):
    pass

  def forward(self, X):
    alphas = np.zeros((self.t, self.n_y))
  
    alpha = np.ones(self.n_y)
    for i in range(self.t):
      alpha = np.dot(alpha, self.score(X[:,i,np.newaxis]))
      alphas[i] = alpha
    return alphas, np.sum(alpha)

  def backward(self, X):
    betas = np.zeros((self.t, self.n_y))
  
    beta = np.repeat(1, self.n_y)
    betas[self.t - 1] = beta
    for i in reversed(range(self.t)):
      beta = np.dot(beta, self.score(X[:,i,np.newaxis]).T)
      if i > 0:
        betas[i-1] = beta
    return betas, np.dot(beta, np.transpose(np.ones(self.n_y)))

  def viterbi(self, X):
    X = self.input_layer.propagate()
    backprobs = np.zeros((self.t, self.n_y))
    backpointers = np.zeros((self.t, self.n_y))
  
    alpha = np.array([1.0, 1.0])
    for i in range(self.t):
      xt = X[:,i,np.newaxis]
      alpha_mat = alpha.reshape((2, 1)) * self.score(xt)
      alpha = np.amax(alpha_mat.T, axis=1)
      pointers = np.argmax(alpha_mat.T, axis=1)
      backprobs[i] = alpha
      backpointers[i] = pointers
  
    last_state = np.argmax(backprobs[self.t - 1])
    res = [last_state]
    for i in range(0, self.t - 1):
      last_state = int(backpointers[self.t - i - 1][last_state])
      res.append(last_state)
      
    res.reverse()
    return res

  def fit(self, Y, learning_rate=0.001, epochs=4500):
    decay = learning_rate / epochs
    for i in range(0, epochs):
      learning_rate *= (1. / (1. + decay * i))
      X = self.input_layer.propagate()

      alphas, n = self.forward(X)
      betas,  n = self.backward(X)
      print 'Negative log likelihood:', self.neg_log_likelihood(X, Y, n)
  
      dWyy = np.zeros((self.n_y, self.n_y))
      dx  = np.zeros((self.n_y, self.t))
      prev_y = np.zeros((self.n_y, 1))
      for i in range(self.t):
        xt = X[:,i,np.newaxis]
        yt = Y[:,i,np.newaxis]

        # Empirical feature count.
        dWyy += np.dot(prev_y, yt.T)
        dx[:,i] = np.ravel(yt)
        prev_y = yt

      # Expected feature count.
      ex_dWyy = np.zeros((self.n_y, self.n_y))
      ex_dx  = np.zeros((self.n_y, self.t))

      alpha = np.array([1, 1])
      for i in range(self.t):
        if i > 0:
          alpha = alphas[i-1]

        my_probs = self.score(X[:,i,np.newaxis])
        beta = betas[i]
        for prev_y, v1 in enumerate(states):
          for y, v2 in enumerate(states):
            ex_dx[:,i][y] += 1 * alpha[prev_y] * my_probs[prev_y][y] * beta[y] / n
            ex_dWyy[prev_y][y] += 1 * alpha[prev_y] * my_probs[prev_y][y] * beta[y] / n

      # print dx
      # print X
      # print ex_dx
      # print dWyy
      # print ex_dWyy
      dx   = -(dx - ex_dx)
      dWyy = -(dWyy - ex_dWyy)
 
      # Update weights.
      self.Wyy -= learning_rate * np.clip(dWyy, -1.0, 1.0, dWyy)
      self.input_layer.backpropagate(dx, learning_rate) 

if __name__ == "__main__":
  X, Y = create_dataset()
  input_layer = InputLayer(3, 2, 3)
  input_layer.set_input(X)
  crf = Crf(2, 3, input_layer)
  crf.fit(Y)
  print labels.tolist()
  print crf.viterbi(X)
