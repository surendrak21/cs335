:p = 20
:q = 10
:r = 5
:s = 15
forward :p
if (:q > :p) [
  :p = 30
  :q = 0
  left :q
  :r = 100
  :s = :s + 10
] else [
  :p = 25
  :q = :q + 5
  right 50
  :r = 200
  :s = :s - 5
]
forward :p
forward :q
forward :r
forward :s
