import torch
import torch.nn as nn
import torch.nn.functional as F
from ShuttleNet.ShuttleNet_layers import DecoderLayer, GatedFusionLayer
from ShuttleNet.ShuttleNet_embedding import PositionalEncoding, PlayerEmbedding, ShotEmbedding


PAD = 0


def get_pad_mask(seq):
    return (seq != PAD).unsqueeze(-2)


def get_subsequent_mask(seq):
    ''' For masking out the subsequent info. '''
    sz_b, len_s = seq.size()
    subsequent_mask = (1 - torch.triu(
        torch.ones((1, len_s, len_s), device=seq.device), diagonal=1)).bool()
    return subsequent_mask


def alternatemerge(seq_A, seq_B, merge_len, player):
    # (batch, seq_len, dim)
    seq_len = seq_A.shape[1]
    merged_seq = torch.zeros(seq_A.shape[0], merge_len, seq_A.shape[2])

    if seq_len * 2 == (merge_len - 1):
        # if seq_len is odd and B will shorter, e.g., merge = 5, A = 3, B = 2
        merged_seq[:, 1::2, :] = seq_A[:, :seq_len, :]
        merged_seq[:, 2::2, :] = seq_B[:, :seq_len, :]
    elif (seq_len * 2 - 1) == merge_len:
        # if seq_len is odd and A will longer, e.g., merge = 5, A = 3, B = 2
        merged_seq[:, ::2, :] = seq_A[:, :seq_len, :]
        merged_seq[:, 1::2, :] = seq_B[:, :merge_len-seq_len, :]
    elif seq_len * 2 == merge_len:
        if player == 'A':
            merged_seq[:, ::2, :] = seq_A[:, :seq_len, :]
            merged_seq[:, 1::2, :] = seq_B[:, :seq_len, :]
        elif player == 'B':
            merged_seq[:, 1::2, :] = seq_A[:, :seq_len, :]
            merged_seq[:, 2::2, :] = seq_B[:, :seq_len-1, :]
        else:
            raise NotImplementedError
    else:
        raise NotImplementedError

    return merged_seq.cuda(seq_A.device)


class ShotGenDecoder(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.area_embedding = nn.Linear(2, config['area_dim'])
        self.shot_embedding = ShotEmbedding(
            config['shot_num'], config['shot_dim'])
        self.player_embedding = PlayerEmbedding(
            config['player_num'], config['player_dim'])

        n_heads = 2
        d_k = config['encode_dim']
        d_v = config['encode_dim']
        d_model = config['encode_dim']
        d_inner = config['encode_dim'] * 2
        dropout = 0.1
        self.d_model = d_model

        self.position_embedding = PositionalEncoding(
            config['shot_dim'], config['encode_length'], n_position=config['max_ball_round'])
        self.dropout = nn.Dropout(p=dropout)

        self.global_layer = DecoderLayer(d_model, d_inner, n_heads, d_k, d_v, dropout=dropout)
        self.local_layer = DecoderLayer(d_model, d_inner,n_heads, d_k, d_v, dropout=dropout)

        self.gated_fusion = GatedFusionLayer(
            d_model, d_model, config['encode_length'], config['max_ball_round'])

    def forward(self, input_shot, input_x, input_y, input_player, encode_local_output, encode_global_A, encode_global_B, trg_mask=None):
        area = torch.cat(
            (input_x.unsqueeze(-1), input_y.unsqueeze(-1)), dim=-1).float()

        # split player only for masking
        mask_A = input_shot[:, ::2]  # even pos
        mask_B = input_shot[:, 1::2]  # odd pos

        # triangular mask
        trg_local_mask = get_pad_mask(input_shot) & get_subsequent_mask(input_shot)
        trg_global_A_mask = get_pad_mask(mask_A) & get_subsequent_mask(mask_A)
        trg_global_B_mask = get_pad_mask(mask_B) & get_subsequent_mask(mask_B)

        embedded_area = F.relu(self.area_embedding(area))
        embedded_shot = self.shot_embedding(input_shot)
        embedded_player = self.player_embedding(input_player)

        h_a = embedded_area + embedded_player
        h_s = embedded_shot + embedded_player

        # split player
        h_a_A = h_a[:, ::2]
        h_a_B = h_a[:, 1::2]
        h_s_A = h_s[:, ::2]
        h_s_B = h_s[:, 1::2]

        # local
        decode_output_area = self.dropout(self.position_embedding(h_a, mode='decode'))
        decode_output_shot = self.dropout(self.position_embedding(h_s, mode='decode'))
        # global
        decode_output_area_A = self.dropout(self.position_embedding(h_a_A, mode='decode'))
        decode_output_area_B = self.dropout(self.position_embedding(h_a_B, mode='decode'))
        decode_output_shot_A = self.dropout(self.position_embedding(h_s_A, mode='decode'))
        decode_output_shot_B = self.dropout(self.position_embedding(h_s_B, mode='decode'))

        decode_global_A = self.global_layer(
            decode_output_area_A, decode_output_shot_A, encode_global_A, slf_attn_mask=trg_global_A_mask)
        if decode_output_area_B.shape[1] != 0:
            decode_global_B = self.global_layer(
                decode_output_area_B, decode_output_shot_B, encode_global_B, slf_attn_mask=trg_global_B_mask)

        decode_local_output = self.local_layer(
            decode_output_area, decode_output_shot, encode_local_output, slf_attn_mask=trg_local_mask)

        if decode_output_area_B.shape[1] != 0:
            decode_output_A = alternatemerge(decode_global_A, decode_global_A, decode_local_output.shape[1], 'A')
            decode_output_B = alternatemerge(decode_global_B, decode_global_B, decode_local_output.shape[1], 'B')
        else:
            decode_output_A = decode_global_A.clone()
            decode_output_B = torch.zeros(decode_local_output.shape, device=decode_local_output.device)
        decode_output = self.gated_fusion(decode_output_A, decode_output_B, decode_local_output)

        return decode_output


class ShotGenPredictor(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.shotgen_decoder = ShotGenDecoder(config)
        self.area_decoder = nn.Sequential(nn.Linear(config['encode_dim'], config['area_num'], bias=False))
        self.shot_decoder = nn.Sequential(nn.Linear(config['encode_dim'], config['shot_num'], bias=False))
        self.player_embedding = PlayerEmbedding(config['player_num'], config['player_dim'])

    def forward(self, input_shot, input_x, input_y, input_player, encode_local_output, encode_global_A, encode_global_B, target_player):
        embedded_target_player = self.player_embedding(target_player)

        decode_output = self.shotgen_decoder(input_shot, input_x, input_y, input_player, encode_local_output, encode_global_A, encode_global_B)

        decode_output = (decode_output + embedded_target_player)

        area_logits = self.area_decoder(decode_output)
        shot_logits = self.shot_decoder(decode_output)


        return area_logits, shot_logits

# 
# class ShotGenEncoder(nn.Module):
#     def __init__(self, config):
#         super().__init__()
#         # dim is 2 * d
#         self.area_embedding = nn.Linear(2, config['area_dim'])
#         # dim is shot * d
#         self.shot_embedding = ShotEmbedding(config['shot_num'], config['shot_dim'])
#         # dim is playerCount * d
#         self.player_embedding = PlayerEmbedding(config['player_num'], config['player_dim'])
# 
#         n_heads = 2
#         d_k = config['encode_dim']
#         d_v = config['encode_dim']
#         d_model = config['encode_dim']
#         d_inner = config['encode_dim'] * 2
#         dropout = 0.1
#         self.d_model = d_model
# 
#         self.position_embedding = PositionalEncoding(
#             config['shot_dim'], config['encode_length'], n_position=config['max_ball_round'])
#         self.dropout = nn.Dropout(p=dropout)
# 
#         self.global_layer = EncoderLayer(d_model, d_inner, n_heads, d_k, d_v, dropout=dropout)
#         self.local_layer = EncoderLayer(d_model, d_inner, n_heads, d_k, d_v, dropout=dropout)
# 
#     def forward(self, input_shot, input_x, input_y, input_player, src_mask=None):
#         '''
#         input_shot   = (dataCount, encodeLength) each shot is int and [1, 10]
#         input_x      = (dataCount, encodeLength) each y is standardlize coord
#         input_y      = (dataCount, encodeLength) each y is standardlize coord
#         input_player = (dataCount, encodeLength) each player is {1,2}
#         '''
#         # area = (dataCount, encodeLength, (x, y))
#         area = torch.cat((input_x.unsqueeze(-1), input_y.unsqueeze(-1)), dim=-1).float()
# 
#         embedded_area = F.relu(self.area_embedding(area))
#         embedded_shot = self.shot_embedding(input_shot)
#         embedded_player = self.player_embedding(input_player)
# 
#         h_a = embedded_area + embedded_player
#         h_s = embedded_shot + embedded_player
#         # print(embedded_area.shape)
#         # print(embedded_player.shape)
#         # print(embedded_shot.shape)
#         # print(h_a.shape)
#         # print(h_s.shape)
# 
#         # split player
#         h_a_A = h_a[:, ::2]     #even
#         h_a_B = h_a[:, 1::2]    #odd
#         h_s_A = h_s[:, ::2]     #even
#         h_s_B = h_s[:, 1::2]    #odd
# 
#         #positional encoding
#         # rally
#         encode_output_area = self.dropout(self.position_embedding(h_a, mode='encode'))
#         encode_output_shot = self.dropout(self.position_embedding(h_s, mode='encode'))
#         # player A
#         encode_output_area_A = self.dropout(self.position_embedding(h_a_A, mode='encode'))
#         encode_output_shot_A = self.dropout(self.position_embedding(h_s_A, mode='encode'))
#         # player B
#         encode_output_area_B = self.dropout(self.position_embedding(h_a_B, mode='encode'))
#         encode_output_shot_B = self.dropout(self.position_embedding(h_s_B, mode='encode'))
# 
#         #multi-head type-area attention & FFN
#         #feed data for one player
#         # player A
#         encode_global_A = self.global_layer(encode_output_area_A, encode_output_shot_A, slf_attn_mask=src_mask)
#         # player B
#         encode_global_B = self.global_layer(encode_output_area_B, encode_output_shot_B, slf_attn_mask=src_mask)
# 
#         # rally
#         encode_local_output = self.local_layer(encode_output_area, encode_output_shot, slf_attn_mask=src_mask)
# 
#         # ablation
#         # encode_local_output = None
#         # encode_global_A, encode_global_B = None, None
# 
#         return encode_local_output, encode_global_A, encode_global_B
# 