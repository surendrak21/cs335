:x = 20
:y = 10
:z = 5
forward :x
if (:y > :x) [
  :x = 30
  :y = 0
  left :y
  :z = 100
] else [
  :x = 25
  :y = :y + 5
  right 50
  :z = 200
]
forward :x
forward :y
forward :z
