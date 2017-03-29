""" An CorpusReader class that interfaces with preprocessed corpora."""

import random

from nltk.metrics import distance

import utils

class CorpusReader:
    """ Interfaces to the preprocessed corpora to read in train, valid, and
    test set features and transcriptions. This interface is common to all
    corpora. It is the responsibility of <corpora-name>.py to preprocess the
    data into a valid structure of
    <corpus-name>/[mam-train|mam-valid<seed>|mam-test].  """

    rand = True

    def __init__(self, corpus, num_train, batch_size=None, max_samples=None, rand_seed=0):
        """ corpus: The Corpus object that interfaces with a given corpus.
            num_train: The number of training instances from the corpus used.
            batch_size: The size of the batches to yield. If None, then it is
                        num_train / 32.0.
            max_samples: The maximum length of utterances measured in samples.
                         Longer utterances are filtered out.
            rand_seed: The seed for the random number generator. If None, then
                       no randomization is used.
        """

        self.corpus = corpus

        if max_samples:
            raise Exception("Not yet implemented.")

        self.num_train = num_train

        if batch_size:
            self.batch_size = batch_size
            if num_train % batch_size != 0:
                raise Exception("""Number of training examples %d not divisible
                                   by batch size %d.""" % (num_train, batch_size))
        else:
            # Dynamically change batch size based on number of training
            # examples.
            self.batch_size = int(num_train / 32.0)
            # For now we hope that training numbers are powers of two or
            # something... If not, crash before anything else happens.
            assert num_train % self.batch_size == 0

        random.seed(rand_seed)

        # Make a copy of the training prefixes, randomize their order, and take
        # a subset. Doing random slection of a subset of training now ensures
        # the selection of of training sentences is invariant between calls to
        # train_batch_gen()
        self.train_fns = list(zip(*corpus.get_train_fns()))
        if self.rand:
            random.shuffle(self.train_fns)
        self.train_fns = self.train_fns[:self.num_train]

    def load_batch(self, fn_batch):
        """ Loads a batch with the given prefix. The prefix is the full path to the
        training example minus the extension.
        """

        feat_fn_batch, target_fn_batch = zip(*fn_batch)

        batch_inputs, batch_inputs_lens = utils.load_batch_x(feat_fn_batch,
                                                             flatten=True)
        batch_targets_list = []
        for targets_path in target_fn_batch:
            with open(targets_path) as targets_f:
                target_indices = self.corpus.phonemes_to_indices(targets_f.readline().split())
                batch_targets_list.append(target_indices)
        batch_targets = utils.target_list_to_sparse_tensor(batch_targets_list)

        return batch_inputs, batch_inputs_lens, batch_targets

    def train_batch_gen(self):
        """ Returns a generator that outputs batches in the training data."""

        # Create batches of batch_size and shuffle them.
        fn_batches = [self.train_fns[i:i+self.batch_size]
                          for i in range(0, len(self.train_fns),
                                         self.batch_size)]

        if self.rand:
            random.shuffle(fn_batches)

        for fn_batch in fn_batches:
            yield self.load_batch(fn_batch)

    def valid_batch(self):
        """ Returns a single batch with all the validation cases."""

        valid_fns = list(zip(*self.corpus.get_valid_fns()))
        return self.load_batch(valid_fns)

    def test_batch(self):
        """ Returns a single batch with all the test cases."""

        test_fns = list(zip(*self.corpus.get_test_fns()))
        return self.load_batch(test_fns)

    def batch_per(self, dense_y, dense_decoded):
        """ Calculates the phoneme error rate of a batch."""

        total_per = 0
        for i in range(len(dense_decoded)):
            ref = [phn_i for phn_i in dense_y[i] if phn_i != 0]
            hyp = [phn_i for phn_i in dense_decoded[i] if phn_i != 0]
            ref = self.corpus.indices_to_phonemes(ref)
            hyp = self.corpus.indices_to_phonemes(hyp)
            total_per += distance.edit_distance(ref, hyp)/len(ref)
        return total_per/len(dense_decoded)
