import optimus

TIME_DIM = 20
VOCAB = 157

# Other code depends on this.
GRAPH_NAME = "classifier-V%03d" % VOCAB


def wcqt_nll():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 6, TIME_DIM, 40))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(16, None, 5, 5),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(20, None, 5, 7),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(24, None, 3, 6),
        act_type='relu')

    layer3 = optimus.Affine(
        name='layer3',
        input_shape=layer2.output.shape,
        output_shape=(None, 512,),
        act_type='relu')

    chord_classifier = optimus.Affine(
        name='chord_classifier',
        input_shape=layer3.output.shape,
        output_shape=(None, VOCAB),
        act_type='softmax')

    param_nodes = [layer0, layer1, layer2, layer3, chord_classifier]

    # 1.1 Create Loss
    target_values = optimus.SelectIndex(name='target_values')

    log = optimus.Log(name='log')
    neg = optimus.Gain(name='gain')
    neg.weight.value = -1.0

    loss = optimus.Mean(name='negative_log_likelihood')

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, chord_classifier.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_classifier.output, target_values.input),
            (chord_idx, target_values.index),
            (target_values.output, log.input),
            (log.output, neg.input),
            (neg.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate],
        nodes=param_nodes + [target_values, log, neg, loss],
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    for n in param_nodes:
        for p in n.params.values():
            optimus.random_init(p)

    posterior = optimus.Output(
        name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_classifier.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def wcqt_nll2():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 5, TIME_DIM, 80))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(32, None, 5, 9),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(64, None, 5, 7),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(128, None, 4, 7),
        act_type='relu')

    layer3 = optimus.Conv3D(
        name='layer3',
        input_shape=layer2.output.shape,
        weight_shape=(13, None, 1, 1),
        act_type='linear')

    reorder = optimus.Flatten('reorder', 2)

    # no_chord = optimus.Affine(
    #     name='no_chord',
    #     input_shape=(None, 128*12*2),
    #     output_shape=(None, 1),
    #     act_type='linear')

    # cat = optimus.Concatenate('concatenate', axis=1)
    softmax = optimus.Softmax('softmax')

    param_nodes = [layer0, layer1, layer2, layer3]
    misc_nodes = [reorder, softmax]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex(name='likelihoods')

    log = optimus.Log(name='log')
    neg = optimus.Gain(name='gain')
    neg.weight.value = -1.0

    loss = optimus.Mean(name='negative_log_likelihood')
    loss_nodes = [likelihoods, log, neg, loss]

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, reorder.input),
        (reorder.output, softmax.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (softmax.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, log.input),
            (log.output, neg.input),
            (neg.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate],
        nodes=param_nodes + misc_nodes + loss_nodes,
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    for n in param_nodes:
        for p in n.params.values():
            optimus.random_init(p)

    posterior = optimus.Output(
        name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(softmax.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes + misc_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def cqt_3layer_convclassifier_smax():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 1, TIME_DIM, 252))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(8, None, 5, 13),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(20, None, 5, 37),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(20, None, 3, 33),
        act_type='relu')

    chord_classifier = optimus.Conv3D(
        name='chord_classifier',
        input_shape=layer2.output.shape,
        weight_shape=(13, None, 2, 1),
        act_type='linear')

    flatten = optimus.Flatten('flatten', 2)

    null_classifier = optimus.Affine(
        name='null_classifier',
        input_shape=layer2.output.shape,
        output_shape=(None, 1),
        act_type='linear')

    cat = optimus.Concatenate('concatenate', num_inputs=2, axis=1)
    softmax = optimus.Softmax('softmax')

    param_nodes = [layer0, layer1, layer2, chord_classifier, null_classifier]
    misc_nodes = [flatten, cat, softmax]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex(name='likelihoods')

    log = optimus.Log(name='log')
    neg = optimus.Gain(name='gain')
    neg.weight.value = -1.0

    loss = optimus.Mean(name='negative_log_likelihood')
    loss_nodes = [likelihoods, log, neg, loss]

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, chord_classifier.input),
        (layer2.output, null_classifier.input),
        (chord_classifier.output, flatten.input),
        (flatten.output, cat.input_0),
        (null_classifier.output, cat.input_1),
        (cat.output, softmax.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (softmax.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, log.input),
            (log.output, neg.input),
            (neg.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate],
        nodes=param_nodes + misc_nodes + loss_nodes,
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    # for n in param_nodes:
    #     for p in n.params.values():
    #         optimus.random_init(p)

    out0 = optimus.Output(name='out0')
    out1 = optimus.Output(name='out1')
    out2 = optimus.Output(name='out2')
    posterior = optimus.Output(name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(softmax.output, posterior),
                      (layer0.output, out0),
                      (layer1.output, out1),
                      (layer2.output, out2)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes + misc_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior, out0, out1, out2])

    return trainer, predictor


def cqt_3layer_allconv_smax_dropout():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 1, TIME_DIM, 252))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    dropout = optimus.Input(
        name='dropout',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(12, None, 5, 13),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(40, None, 5, 37),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(40, None, 4, 33),
        act_type='relu')

    chord_classifier = optimus.Conv3D(
        name='chord_classifier',
        input_shape=layer2.output.shape,
        weight_shape=(13, None, 1, 1),
        act_type='linear')

    flatten = optimus.Flatten('flatten', 2)

    null_classifier = optimus.Affine(
        name='null_classifier',
        input_shape=layer2.output.shape,
        output_shape=(None, 1),
        act_type='linear')

    cat = optimus.Concatenate('concatenate', num_inputs=2, axis=1)
    softmax = optimus.Softmax('softmax')

    param_nodes = [layer0, layer1, layer2, chord_classifier, null_classifier]
    misc_nodes = [flatten, cat, softmax]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex(name='likelihoods')

    log = optimus.Log(name='log')
    neg = optimus.Gain(name='gain')
    neg.weight.value = -1.0

    loss = optimus.Mean(name='negative_log_likelihood')
    loss_nodes = [likelihoods, log, neg, loss]

    layer0.enable_dropout()
    layer1.enable_dropout()
    layer2.enable_dropout()

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, chord_classifier.input),
        (layer2.output, null_classifier.input),
        (chord_classifier.output, flatten.input),
        (flatten.output, cat.input_0),
        (null_classifier.output, cat.input_1),
        (cat.output, softmax.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (dropout, layer0.dropout),
            (dropout, layer1.dropout),
            (dropout, layer2.dropout),
            (softmax.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, log.input),
            (log.output, neg.input),
            (neg.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate, dropout],
        nodes=param_nodes + misc_nodes + loss_nodes,
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    # for n in param_nodes:
    #     for p in n.params.values():
    #         optimus.random_init(p)

    layer0.disable_dropout()
    layer1.disable_dropout()
    layer2.disable_dropout()

    out0 = optimus.Output(name='out0')
    out1 = optimus.Output(name='out1')
    out2 = optimus.Output(name='out2')
    posterior = optimus.Output(name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(softmax.output, posterior),
                      (layer0.output, out0),
                      (layer1.output, out1),
                      (layer2.output, out2)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes + misc_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior, out0, out1, out2])

    return trainer, predictor


def cqt_3layer_convclassifier_smax_smce():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 1, TIME_DIM, 252))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(8, None, 5, 13),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(20, None, 5, 37),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(20, None, 3, 33),
        act_type='relu')

    chord_classifier = optimus.Conv3D(
        name='chord_classifier',
        input_shape=layer2.output.shape,
        weight_shape=(13, None, 2, 1),
        act_type='linear')

    flatten = optimus.Flatten('flatten', 2)

    null_classifier = optimus.Affine(
        name='null_classifier',
        input_shape=layer2.output.shape,
        output_shape=(None, 1),
        act_type='linear')

    cat = optimus.Concatenate('concatenate', num_inputs=2, axis=1)
    softmax = optimus.Softmax('softmax')

    param_nodes = [layer0, layer1, layer2, chord_classifier, null_classifier]
    misc_nodes = [flatten, cat, softmax]

    # 1.1 Create Loss
    log = optimus.Log(name='log')
    neg_one0 = optimus.Gain(name='neg_one0')
    neg_one0.weight.value = -1.0

    target_values = optimus.SelectIndex(name='target_values')
    moia_values = optimus.MinNotIndex(name="moia_values")

    neg_one1 = optimus.Gain(name='neg_one1')
    neg_one1.weight.value = -1.0
    summer = optimus.Accumulate(name='summer', num_inputs=2)

    soft_step = optimus.SoftRectifiedLinear(name='soft_step', knee=5.0)
    loss = optimus.Mean(name='mce_loss')

    loss_nodes = [log, neg_one0, target_values, moia_values,
                  neg_one1, summer, soft_step, loss]

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, chord_classifier.input),
        (layer2.output, null_classifier.input),
        (chord_classifier.output, flatten.input),
        (flatten.output, cat.input_0),
        (null_classifier.output, cat.input_1),
        (cat.output, softmax.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (softmax.output, log.input),
            (log.output, neg_one0.input),
            (neg_one0.output, target_values.input),
            (chord_idx, target_values.index),
            (neg_one0.output, moia_values.input),
            (chord_idx, moia_values.index),
            (target_values.output, summer.input_0),
            (moia_values.output, neg_one1.input),
            (neg_one1.output, summer.input_1),
            (summer.output, soft_step.input),
            (soft_step.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate],
        nodes=param_nodes + misc_nodes + loss_nodes,
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    # for n in param_nodes:
    #     for p in n.params.values():
    #         optimus.random_init(p)

    # out0 = optimus.Output(name='out0')
    # out1 = optimus.Output(name='out1')
    # out2 = optimus.Output(name='out2')
    posterior = optimus.Output(name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(softmax.output, posterior)])
                      # (layer0.output, out0),
                      # (layer1.output, out1),
                      # (layer2.output, out2)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes + misc_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def cqt_nll_margin():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 1, TIME_DIM, 252))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    margin = optimus.Input(
        name='margin',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(6, None, 5, 7),  # or 13
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(20, None, 5, 15),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(20, None, 3, 15),
        act_type='relu')

    layer3 = optimus.Affine(
        name='layer3',
        input_shape=layer2.output.shape,
        output_shape=(None, 512,),
        act_type='relu')

    chord_estimator = optimus.Affine(
        name='chord_estimator',
        input_shape=layer3.output.shape,
        output_shape=(None, VOCAB),
        act_type='sigmoid')

    param_nodes = [layer0, layer1, layer2, layer3, chord_estimator]

    # 1.1 Create Loss
    log = optimus.Log(name='log')
    neg_one0 = optimus.Gain(name='neg_one0')
    neg_one0.weight.value = -1.0

    target_values = optimus.SelectIndex(name='target_values')
    moia_values = optimus.MinNotIndex(name="moia_values")

    neg_one1 = optimus.Gain(name='neg_one1')
    neg_one1.weight.value = -1.0
    summer = optimus.Accumulate(name='summer')

    relu = optimus.RectifiedLinear(name='relu')
    loss = optimus.Mean(name='margin_loss')

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, chord_estimator.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_estimator.output, log.input),
            (log.output, neg_one0.input),
            (neg_one0.output, target_values.input),
            (chord_idx, target_values.index),
            (neg_one0.output, moia_values.input),
            (chord_idx, moia_values.index),
            (margin, summer.input_list),
            (target_values.output, summer.input_list),
            (moia_values.output, neg_one1.input),
            (neg_one1.output, summer.input_list),
            (summer.output, relu.input),
            (relu.output, loss.input)])

    updates = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate, margin],
        nodes=param_nodes + [log, neg_one0, target_values, moia_values,
                             neg_one1, summer, relu, loss],
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=updates.connections,
        verbose=True)

    for n in param_nodes:
        for p in n.params.values():
            optimus.random_init(p)

    posterior = optimus.Output(
        name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_estimator.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def wcqt_nll_margin():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 6, TIME_DIM, 40))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    margin = optimus.Input(
        name='margin',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(32, None, 5, 5),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(64, None, 5, 7),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(128, None, 3, 6),
        act_type='relu')

    layer3 = optimus.Affine(
        name='layer3',
        input_shape=layer2.output.shape,
        output_shape=(None, 1024,),
        act_type='relu')

    chord_classifier = optimus.Affine(
        name='chord_estimator',
        input_shape=layer3.output.shape,
        output_shape=(None, VOCAB),
        act_type='sigmoid')

    param_nodes = [layer0, layer1, layer2, layer3, chord_classifier]

    # 1.1 Create Loss
    log = optimus.Log(name='log')
    neg_one0 = optimus.Gain(name='neg_one0')
    neg_one0.weight.value = -1.0

    target_values = optimus.SelectIndex(name='target_values')
    moia_values = optimus.MinNotIndex(name="moia_values")

    neg_one1 = optimus.Gain(name='neg_one1')
    neg_one1.weight.value = -1.0
    summer = optimus.Accumulate(name='summer')

    relu = optimus.RectifiedLinear(name='relu')
    loss = optimus.Mean(name='margin_loss')

    target_vals = optimus.Output(
        name='target_vals')

    moia_vals = optimus.Output(
        name='moia_vals')

    summer_vals = optimus.Output(
        name='summer_vals')

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, chord_classifier.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_classifier.output, log.input),
            (log.output, neg_one0.input),
            (neg_one0.output, target_values.input),
            (chord_idx, target_values.index),
            (neg_one0.output, moia_values.input),
            (chord_idx, moia_values.index),
            (margin, summer.input_list),
            (target_values.output, summer.input_list),
            (target_values.output, target_vals),
            (moia_values.output, neg_one1.input),
            (moia_values.output, moia_vals),
            (neg_one1.output, summer.input_list),
            (summer.output, relu.input),
            (summer.output, summer_vals),
            (relu.output, loss.input)])

    updates = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate, margin],
        nodes=param_nodes + [log, neg_one0, target_values, moia_values,
                             neg_one1, summer, relu, loss],
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=updates.connections,
        verbose=True)

    for n in param_nodes:
        for p in n.params.values():
            optimus.random_init(p)

    posterior = optimus.Output(
        name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_classifier.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def wcqt_sigmoid_mse(n_dim=VOCAB):
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 6, TIME_DIM, 40))

    target = optimus.Input(
        name='target',
        shape=(None, n_dim))

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(32, None, 5, 5),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(64, None, 5, 7),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(128, None, 3, 6),
        act_type='relu')

    layer3 = optimus.Affine(
        name='layer3',
        input_shape=layer2.output.shape,
        output_shape=(None, 1024,),
        act_type='relu')

    chord_estimator = optimus.Affine(
        name='chord_estimator',
        input_shape=layer3.output.shape,
        output_shape=(None, n_dim),
        act_type='sigmoid')

    param_nodes = [layer0, layer1, layer2, layer3, chord_estimator]

    # 1.1 Create Loss
    error = optimus.SquaredEuclidean(name='squared_error')
    loss = optimus.Mean(name='mean_squared_error')

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, chord_estimator.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_estimator.output, error.input_a),
            (target, error.input_b),
            (error.output, loss.input)])

    # update_manager = optimus.ConnectionManager(
    #     map(lambda n: (learning_rate, n.weights), param_nodes) +
    #     map(lambda n: (learning_rate, n.bias), param_nodes))
    update_manager = optimus.ConnectionManager(
        [(learning_rate, chord_estimator.bias)])

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, target, learning_rate],
        nodes=param_nodes + [error, loss],
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    for n in param_nodes:
        for p in n.params.values():
            optimus.random_init(p)

    posterior = optimus.Output(
        name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_estimator.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def cqt_smax_3layer(n_dim=VOCAB):
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 1, TIME_DIM, 252))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(8, None, 5, 13),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(24, None, 5, 37),
        act_type='relu')

    layer2 = optimus.Affine(
        name='layer2',
        input_shape=layer1.output.shape,
        output_shape=(None, 512,),
        act_type='relu')

    chord_classifier = optimus.Affine(
        name='chord_classifier',
        input_shape=layer2.output.shape,
        output_shape=(None, n_dim),
        act_type='softmax')

    param_nodes = [layer0, layer1, layer2, chord_classifier]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex(name='likelihoods')

    log = optimus.Log(name='log')
    neg = optimus.Gain(name='gain')
    neg.weight.value = -1.0

    loss = optimus.Mean(name='negative_log_likelihood')

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, chord_classifier.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_classifier.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, log.input),
            (log.output, neg.input),
            (neg.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate],
        nodes=param_nodes + [likelihoods, neg, log, loss],
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    # out0 = optimus.Output(name='out0')
    # out1 = optimus.Output(name='out1')
    # out2 = optimus.Output(name='out2')
    posterior = optimus.Output(name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_classifier.output, posterior)])
                      # (layer0.output, out0),
                      # (layer1.output, out1),
                      # (layer2.output, out2)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def cqt_smax_3layer_mce(n_dim=VOCAB):
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 1, TIME_DIM, 252))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(8, None, 5, 13),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(24, None, 5, 37),
        act_type='relu')

    layer2 = optimus.Affine(
        name='layer2',
        input_shape=layer1.output.shape,
        output_shape=(None, 512,),
        act_type='relu')

    chord_classifier = optimus.Affine(
        name='chord_classifier',
        input_shape=layer2.output.shape,
        output_shape=(None, n_dim),
        act_type='softmax')

    param_nodes = [layer0, layer1, layer2, chord_classifier]

    # 1.1 Create Loss
    log = optimus.Log(name='log')
    neg_one0 = optimus.Gain(name='neg_one0')
    neg_one0.weight.value = -1.0

    target_values = optimus.SelectIndex(name='target_values')
    moia_values = optimus.MinNotIndex(name="moia_values")

    neg_one1 = optimus.Gain(name='neg_one1')
    neg_one1.weight.value = -1.0
    summer = optimus.Accumulate(name='summer', num_inputs=2)

    soft_step = optimus.Sigmoid(name='soft_step')
    loss = optimus.Mean(name='mce_loss')

    loss_nodes = [log, neg_one0, target_values, moia_values,
                  neg_one1, summer, soft_step, loss]

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, chord_classifier.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_classifier.output, log.input),
            (log.output, neg_one0.input),
            (neg_one0.output, target_values.input),
            (chord_idx, target_values.index),
            (neg_one0.output, moia_values.input),
            (chord_idx, moia_values.index),
            (target_values.output, summer.input_0),
            (moia_values.output, neg_one1.input),
            (neg_one1.output, summer.input_1),
            (summer.output, soft_step.input),
            (soft_step.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, learning_rate],
        nodes=param_nodes + loss_nodes,
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    out0 = optimus.Output(name='out0')
    out1 = optimus.Output(name='out1')
    out2 = optimus.Output(name='out2')
    posterior = optimus.Output(name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_classifier.output, posterior),
                      (layer0.output, out0),
                      (layer1.output, out1),
                      (layer2.output, out2)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[out0, out1, out2, posterior])

    return trainer, predictor


def cqt_likelihood(n_dim=VOCAB):
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 1, TIME_DIM, 252))

    target = optimus.Input(
        name='target',
        shape=(None, 1))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(6, None, 5, 7),  # or 13
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(20, None, 5, 15),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(20, None, 3, 15),
        act_type='relu')

    layer3 = optimus.Affine(
        name='layer3',
        input_shape=layer2.output.shape,
        output_shape=(None, 512,),
        act_type='relu')

    chord_estimator = optimus.Affine(
        name='chord_estimator',
        input_shape=layer3.output.shape,
        output_shape=(None, n_dim),
        act_type='sigmoid')

    param_nodes = [layer0, layer1, layer2, layer3, chord_estimator]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex('select')
    dimshuffle = optimus.Dimshuffle('dimshuffle', (0, 'x'))
    error = optimus.SquaredEuclidean(name='squared_error')
    loss = optimus.Mean(name='mean_squared_error')

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, chord_estimator.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_estimator.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, dimshuffle.input),
            (dimshuffle.output, error.input_a),
            (target, error.input_b),
            (error.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, target, chord_idx, learning_rate],
        nodes=param_nodes + [likelihoods, dimshuffle, error, loss],
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    posterior = optimus.Output(name='posterior')
    out0 = optimus.Output(name='out0')
    out1 = optimus.Output(name='out1')
    out2 = optimus.Output(name='out2')
    out3 = optimus.Output(name='out3')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_estimator.output, posterior),
                      (layer0.output, out0),
                      (layer1.output, out1),
                      (layer2.output, out2),
                      (layer3.output, out3)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[out0, out1, out2, out3, posterior])

    return trainer, predictor


def wcqt_likelihood(n_dim=VOCAB):
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 6, TIME_DIM, 40))

    target = optimus.Input(
        name='target',
        shape=(None, 1))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(12, None, 5, 5),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(16, None, 5, 7),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(20, None, 3, 6),
        act_type='relu')

    layer3 = optimus.Affine(
        name='layer3',
        input_shape=layer2.output.shape,
        output_shape=(None, 512,),
        act_type='relu')

    chord_estimator = optimus.Affine(
        name='chord_estimator',
        input_shape=layer3.output.shape,
        output_shape=(None, n_dim),
        act_type='sigmoid')

    param_nodes = [layer0, layer1, layer2, layer3, chord_estimator]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex('select')
    dimshuffle = optimus.Dimshuffle('dimshuffle', (0, 'x'))
    error = optimus.SquaredEuclidean(name='squared_error')
    loss = optimus.Mean(name='mean_squared_error')

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, chord_estimator.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_estimator.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, dimshuffle.input),
            (dimshuffle.output, error.input_a),
            (target, error.input_b),
            (error.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, target, chord_idx, learning_rate],
        nodes=param_nodes + [likelihoods, dimshuffle, error, loss],
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    for n in layer0, layer1, layer2:
        for p in n.params.values():
            optimus.random_init(p, 0.01, 0.01)

    for p in layer3.params.values():
        optimus.random_init(p, 0.01, 0.001)

    for p in chord_estimator.params.values():
        optimus.random_init(p, 0.0, 0.001)

    posterior = optimus.Output(name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_estimator.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def wcqt_likelihood2():
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 5, TIME_DIM, 80))

    target = optimus.Input(
        name='target',
        shape=(None, 1))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(12, None, 5, 9),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(16, None, 5, 7),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(20, None, 4, 7),
        act_type='relu')

    layer3 = optimus.Conv3D(
        name='layer3',
        input_shape=layer2.output.shape,
        weight_shape=(13, None, 1, 1),
        act_type='sigmoid')

    reorder = optimus.Flatten('reorder', 2)

    # no_chord = optimus.Affine(
    #     name='no_chord',
    #     input_shape=(None, 128*12),
    #     output_shape=(None, 1),
    #     act_type='sigmoid')

    # cat = optimus.Concatenate('concatenate', axis=1)

    param_nodes = [layer0, layer1, layer2, layer3]
    misc_nodes = [reorder]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex('select')
    dimshuffle = optimus.Dimshuffle('dimshuffle', (0, 'x'))
    error = optimus.SquaredEuclidean(name='squared_error')
    loss = optimus.Mean(name='mean_squared_error')

    loss_nodes = [likelihoods, dimshuffle, error, loss]

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, reorder.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (reorder.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, dimshuffle.input),
            (dimshuffle.output, error.input_a),
            (target, error.input_b),
            (error.output, loss.input)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, chord_idx, target, learning_rate],
        nodes=param_nodes + misc_nodes + loss_nodes,
        connections=trainer_edges.connections,
        outputs=[loss.output],
        loss=loss.output,
        updates=update_manager.connections,
        verbose=True)

    for n in param_nodes:
        for p in n.params.values():
            optimus.random_init(p)

    posterior = optimus.Output(name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(reorder.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes + misc_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


def wcqt_likelihood_wmoia(n_dim=VOCAB):
    input_data = optimus.Input(
        name='cqt',
        shape=(None, 6, TIME_DIM, 40))

    target = optimus.Input(
        name='target',
        shape=(None, 1))

    chord_idx = optimus.Input(
        name='chord_idx',
        shape=(None,),
        dtype='int32')

    learning_rate = optimus.Input(
        name='learning_rate',
        shape=None)

    moia_weight = optimus.Input(
        name='moia_weight',
        shape=None)

    # 1.2 Create Nodes
    layer0 = optimus.Conv3D(
        name='layer0',
        input_shape=input_data.shape,
        weight_shape=(32, None, 5, 5),
        pool_shape=(2, 3),
        act_type='relu')

    layer1 = optimus.Conv3D(
        name='layer1',
        input_shape=layer0.output.shape,
        weight_shape=(64, None, 5, 7),
        act_type='relu')

    layer2 = optimus.Conv3D(
        name='layer2',
        input_shape=layer1.output.shape,
        weight_shape=(128, None, 3, 6),
        act_type='relu')

    layer3 = optimus.Affine(
        name='layer3',
        input_shape=layer2.output.shape,
        output_shape=(None, 1024,),
        act_type='relu')

    chord_estimator = optimus.Affine(
        name='chord_estimator',
        input_shape=layer3.output.shape,
        output_shape=(None, n_dim),
        act_type='sigmoid')

    param_nodes = [layer0, layer1, layer2, layer3, chord_estimator]

    # 1.1 Create Loss
    likelihoods = optimus.SelectIndex('select')
    dimshuffle = optimus.Dimshuffle('dimshuffle', (0, 'x'))
    error = optimus.SquaredEuclidean(name='squared_error')
    main_loss = optimus.Mean(name='mean_squared_error')
    loss_nodes1 = [likelihoods, dimshuffle, error, main_loss]

    negone = optimus.Gain(name='negate')
    negone.weight.value = -1.0
    summer = optimus.Accumulate(name='moia_sum')
    flatten = optimus.Sum('flatten', axis=1)
    dimshuffle2 = optimus.Dimshuffle('dimshuffle2', (0, 'x'))
    margin = optimus.RectifiedLinear(name='margin')
    weight = optimus.Multiply(name="margin_weight")
    margin_loss = optimus.Mean(name='margin_loss', axis=None)

    loss_nodes2 = [negone, summer, margin, flatten,
                   dimshuffle2, margin_loss, weight]
    total_loss = optimus.Accumulate("total_loss")

    # 2. Define Edges
    base_edges = [
        (input_data, layer0.input),
        (layer0.output, layer1.input),
        (layer1.output, layer2.input),
        (layer2.output, layer3.input),
        (layer3.output, chord_estimator.input)]

    trainer_edges = optimus.ConnectionManager(
        base_edges + [
            (chord_estimator.output, likelihoods.input),
            (chord_idx, likelihoods.index),
            (likelihoods.output, dimshuffle.input),
            (dimshuffle.output, error.input_a),
            (target, error.input_b),
            (error.output, main_loss.input),
            # Margin loss
            (dimshuffle.output, negone.input),
            (negone.output, summer.input_list),
            (chord_estimator.output, summer.input_list),
            (summer.output, margin.input),
            (margin.output, flatten.input),
            (flatten.output, dimshuffle2.input),
            (dimshuffle2.output, weight.input_a),
            (target, weight.input_b),
            (weight.output, margin_loss.input),
            (margin_loss.output, total_loss.input_list),
            (main_loss.output, total_loss.input_list)])

    update_manager = optimus.ConnectionManager(
        map(lambda n: (learning_rate, n.weights), param_nodes) +
        map(lambda n: (learning_rate, n.bias), param_nodes))

    all_nodes = param_nodes + loss_nodes1 + loss_nodes2 + [total_loss]
    trainer = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data, target, chord_idx, learning_rate],
        nodes=all_nodes,
        connections=trainer_edges.connections,
        outputs=[total_loss.output],
        loss=total_loss.output,
        updates=update_manager.connections,
        verbose=True)

    for n in param_nodes:
        for p in n.params.values():
            optimus.random_init(p)

    posterior = optimus.Output(
        name='posterior')

    predictor_edges = optimus.ConnectionManager(
        base_edges + [(chord_estimator.output, posterior)])

    predictor = optimus.Graph(
        name=GRAPH_NAME,
        inputs=[input_data],
        nodes=param_nodes,
        connections=predictor_edges.connections,
        outputs=[posterior])

    return trainer, predictor


MODELS = {
    'wcqt_nll': wcqt_nll,
    'wcqt_nll2': wcqt_nll2,
    'cqt_smax_3layer': cqt_smax_3layer,
    'cqt_smax_3layer_mce': cqt_smax_3layer_mce,
    'cqt_3layer_convclassifier_smax': cqt_3layer_convclassifier_smax,
    'cqt_3layer_allconv_smax_dropout': cqt_3layer_allconv_smax_dropout,
    'cqt_3layer_convclassifier_smax_smce': cqt_3layer_convclassifier_smax_smce,
    'cqt_nll_margin': cqt_nll_margin,
    'wcqt_nll_margin': wcqt_nll_margin,
    'wcqt_sigmoid_mse': wcqt_sigmoid_mse,
    'cqt_likelihood': cqt_likelihood,
    'wcqt_likelihood': wcqt_likelihood,
    'wcqt_likelihood2': wcqt_likelihood2,
    'wcqt_likelihood_wmoia': wcqt_likelihood_wmoia}