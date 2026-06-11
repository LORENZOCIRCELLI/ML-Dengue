class LSTMCell:
    def __init__(self, input_size, hidden_size, seed=42):
        rng = np.random.default_rng(seed)

        scale_i = np.sqrt(2.0 / (input_size + hidden_size))
        scale_h = np.sqrt(2.0 / (hidden_size + hidden_size))

        self.Wf = rng.normal(0, scale_i, (hidden_size, input_size))
        self.Uf = rng.normal(0, scale_h, (hidden_size, hidden_size))
        self.bf = np.zeros((hidden_size, 1))

        self.Wi = rng.normal(0, scale_i, (hidden_size, input_size))
        self.Ui = rng.normal(0, scale_h, (hidden_size, hidden_size))
        self.bi = np.zeros((hidden_size, 1))

        self.Wg = rng.normal(0, scale_i, (hidden_size, input_size))
        self.Ug = rng.normal(0, scale_h, (hidden_size, hidden_size))
        self.bg = np.zeros((hidden_size, 1))

        self.Wo = rng.normal(0, scale_i, (hidden_size, input_size))
        self.Uo = rng.normal(0, scale_h, (hidden_size, hidden_size))
        self.bo = np.zeros((hidden_size, 1))

        self.Wy = rng.normal(
            0,
            np.sqrt(2.0 / hidden_size),
            (1, hidden_size)
        )

        self.by = np.zeros((1, 1))

        self.hidden_size = hidden_size
        self.input_size = input_size

    @staticmethod
    def sigmoid(x):
        return 1 / (1 + np.exp(-np.clip(x, -500, 500)))

    @staticmethod
    def tanh(x):
        return np.tanh(np.clip(x, -500, 500))

    def forward_sequence(self, X_seq):
        h = np.zeros((self.hidden_size, 1))
        c = np.zeros((self.hidden_size, 1))

        for t in range(len(X_seq)):
            x = X_seq[t].reshape(-1, 1)

            f = self.sigmoid(self.Wf @ x + self.Uf @ h + self.bf)
            i = self.sigmoid(self.Wi @ x + self.Ui @ h + self.bi)
            g = self.tanh(self.Wg @ x + self.Ug @ h + self.bg)
            o = self.sigmoid(self.Wo @ x + self.Uo @ h + self.bo)

            c = f * c + i * g
            h = o * self.tanh(c)

        y = self.sigmoid(self.Wy @ h + self.by)

        return y.item(), h, c

    def predict_batch(self, X_sequences):
        preds = []

        for seq in X_sequences:
            prob, _, _ = self.forward_sequence(seq)
            preds.append(prob)

        return np.array(preds)

top_lstm_features_candidates = perm_df['feature'].head(10).tolist()

core_climate = [
    'media_temperatura_semana',
    'chuva_total_mm',
    'media_umidade_semana',
    'ONI',
    'semana_sin',
    'semana_cos'
]

lstm_features = list(
    dict.fromkeys(
        top_lstm_features_candidates +
        [f for f in core_climate if f in feature_cols]
    )
)

lstm_features = [
    f for f in lstm_features
    if f in feature_cols
][:15]

lstm_scaler = MinMaxScaler()

X_lstm_all = (
    fe_clean[lstm_features]
    .ffill()
    .bfill()
    .fillna(0)
)

X_lstm_all_sc = lstm_scaler.fit_transform(X_lstm_all)

y_lstm_all = fe_clean[LABEL_COL].astype(int).values

SEQ_LEN = 12

def build_sequences(X_arr, y_arr, seq_len):
    Xs = []
    ys = []

    for i in range(seq_len, len(X_arr)):
        Xs.append(X_arr[i - seq_len:i])
        ys.append(y_arr[i])

    return np.array(Xs), np.array(ys)

X_seq, y_seq = build_sequences(
    X_lstm_all_sc,
    y_lstm_all,
    SEQ_LEN
)

split_seq = int(len(X_seq) * 0.80)

X_seq_train = X_seq[:split_seq]
X_seq_test = X_seq[split_seq:]

y_seq_train = y_seq[:split_seq]
y_seq_test = y_seq[split_seq:]

def binary_cross_entropy(y_true, y_pred, eps=1e-9):
    y_pred = np.clip(y_pred, eps, 1 - eps)
    return -np.mean(
        y_true * np.log(y_pred) +
        (1 - y_true) * np.log(1 - y_pred)
    )

N_FEATURES = len(lstm_features)
HIDDEN_SIZE = 32

lstm = LSTMCell(
    input_size=N_FEATURES,
    hidden_size=HIDDEN_SIZE,
    seed=42
)

EPOCHS = 50
BATCH_SIZE = 16
LR = 0.01
EPS_GRAD = 1e-5

train_losses = []
val_losses = []

n_outbreak = y_seq_train.sum()
n_normal = len(y_seq_train) - n_outbreak

pos_weight = n_normal / max(n_outbreak, 1)

sample_wts = np.where(
    y_seq_train == 1,
    pos_weight,
    1.0
)

sample_wts /= sample_wts.sum()

def get_all_weights(model):
    return [
        model.Wf, model.Uf, model.bf,
        model.Wi, model.Ui, model.bi,
        model.Wg, model.Ug, model.bg,
        model.Wo, model.Uo, model.bo,
        model.Wy, model.by
    ]

def set_weight_val(model, wlist, i, j, k, val):
    wlist[i][j, k] = val

def numerical_grad_single(
    model,
    seq,
    y_true,
    weight_list,
    w_idx,
    i,
    j,
    eps=EPS_GRAD
):
    orig = weight_list[w_idx][i, j]

    weight_list[w_idx][i, j] = orig + eps
    yp_plus, _, _ = model.forward_sequence(seq)

    loss_plus = -(
        y_true * np.log(max(yp_plus, 1e-9)) +
        (1 - y_true) * np.log(max(1 - yp_plus, 1e-9))
    )

    weight_list[w_idx][i, j] = orig - eps
    yp_minus, _, _ = model.forward_sequence(seq)

    loss_minus = -(
        y_true * np.log(max(yp_minus, 1e-9)) +
        (1 - y_true) * np.log(max(1 - yp_minus, 1e-9))
    )

    weight_list[w_idx][i, j] = orig

    return (loss_plus - loss_minus) / (2 * eps)

rng = np.random.default_rng(42)

for epoch in range(EPOCHS):
    idx = rng.choice(
        len(X_seq_train),
        size=len(X_seq_train),
        replace=False,
        p=sample_wts
    )

    epoch_loss = 0.0

    for b_start in range(0, len(idx), BATCH_SIZE):
        batch_idx = idx[b_start:b_start + BATCH_SIZE]

        grad_Wy = np.zeros_like(lstm.Wy)
        grad_by = np.zeros_like(lstm.by)

        batch_loss = 0.0

        for bi in batch_idx:
            seq = X_seq_train[bi]
            y_true = float(y_seq_train[bi])

            y_pred, h, c = lstm.forward_sequence(seq)
            y_pred = np.clip(y_pred, 1e-9, 1 - 1e-9)

            loss = -(
                y_true * np.log(y_pred) +
                (1 - y_true) * np.log(1 - y_pred)
            )

            batch_loss += loss

            dL_dy = -(
                y_true / y_pred -
                (1 - y_true) / (1 - y_pred)
            )

            dlogit = dL_dy * y_pred * (1 - y_pred)

            grad_Wy += dlogit * h.T
            grad_by += dlogit

        n_batch = max(len(batch_idx), 1)

        lstm.Wy -= LR * grad_Wy / n_batch
        lstm.by -= LR * grad_by / n_batch

        epoch_loss += batch_loss / n_batch

    val_preds = lstm.predict_batch(X_seq_test)
    val_loss = binary_cross_entropy(y_seq_test, val_preds)

    train_losses.append(
        float(epoch_loss) /
        max(len(X_seq_train) // BATCH_SIZE, 1)
    )

    val_losses.append(float(val_loss))