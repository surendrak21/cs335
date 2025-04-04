:p = 10
:q = 5
:r = 3
:s = 2
:t = 1

forward :p

if (:q > :r) [
  :p = 100
  :q = 200
  :r = 300
  :s = 400
  :t = 500
  left :p
] else [
  :p = 110
  :q = 210
  :r = 310
  :s = 410
  :t = 510
  right :q
]

forward :p
forward :q
forward :r
forward :s
forward :t
